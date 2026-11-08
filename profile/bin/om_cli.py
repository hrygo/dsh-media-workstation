#!/usr/bin/env python3
"""om — OpenMontage bridge for the DSH media preset.

Thin, dependency-light CLI over OpenMontage's local tools. It deliberately
exposes only the editing/ledger half of OpenMontage:

  pipelines            list pipeline manifests
  skills <pipeline>    list stage director skills (paths, or --show content)
  validate <json>      schema + asset check via composition_validator
  compose <json>       render cuts via video_compose (ffmpeg path only)
  probe <media>        ffprobe summary + optional assertions
  doctor               environment check

Generation stays with mcp__comfyui__; speech stays with SpeechRail.
"""

from __future__ import annotations

import argparse
import json
import re
import os
import shutil
import subprocess
import sys
from pathlib import Path

OM_HOME = Path(
    os.environ.get("OPENMONTAGE_HOME") or (Path.home() / "OpenMontage")
).resolve()


def _load_yaml():
    import yaml  # noqa: PLC0415

    return yaml


def _tool_result(result) -> dict:
    return {
        "success": bool(getattr(result, "success", False)),
        "error": getattr(result, "error", None),
        "data": getattr(result, "data", None) or {},
        "warnings": getattr(result, "warnings", None) or [],
        "cost_usd": getattr(result, "cost_usd", None),
    }


def cmd_pipelines(args) -> int:
    yaml = _load_yaml()
    rows = []
    for path in sorted((OM_HOME / "pipeline_defs").glob("*.yaml")):
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as exc:  # noqa: BLE001
            rows.append({"file": path.name, "error": str(exc)})
            continue
        stages = doc.get("stages") or []
        rows.append(
            {
                "file": path.name,
                "name": doc.get("name") or path.stem,
                "category": doc.get("category"),
                "stability": doc.get("stability"),
                "stages": [s.get("name") for s in stages],
                "gate_stages": [
                    s.get("name") for s in stages if s.get("checkpoint_required")
                ],
            }
        )
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    for row in rows:
        if "error" in row:
            print(f"{row['file']:32s} ERROR {row['error']}")
            continue
        print(f"{row['name']:24s} {len(row['stages']):2d} 阶段  {row['category']}")
        print(f"   阶段: {' -> '.join(row['stages'])}")
        if row["gate_stages"]:
            print(f"   门: {' '.join(row['gate_stages'])}")
    return 0


def cmd_skills(args) -> int:
    yaml = _load_yaml()
    names = [args.pipeline] if args.pipeline else [
        p.stem for p in sorted((OM_HOME / "pipeline_defs").glob("*.yaml"))
    ]
    found = 0
    for name in names:
        manifest = OM_HOME / "pipeline_defs" / f"{name}.yaml"
        if not manifest.exists():
            print(f"未知管道: {name}", file=sys.stderr)
            continue
        doc = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
        print(f"# {doc.get('name') or name}")
        for stage in doc.get("stages") or []:
            skill = stage.get("skill") or ""
            path = OM_HOME / "skills" / f"{skill}.md"
            state = "ok" if path.is_file() else "missing"
            print(f"  {stage.get('name'):16s} {state:8s} {path}")
            found += 1
            if args.show and path.is_file():
                text = path.read_text(encoding="utf-8")
                limit = args.show if isinstance(args.show, int) else 4000
                print(text[:limit])
    return 0 if found else 1


_SCHEMA_PATH = OM_HOME / "schemas" / "artifacts" / "edit_decisions.schema.json"


def _duration_seconds(path: Path) -> float:
    try:
        info = _ffprobe(path)
        return float(((info.get("format") or {}).get("duration")) or 0.0)
    except Exception:  # noqa: BLE001
        return 0.0


def _apply_schema_check(out: dict, composition: Path) -> None:
    """Enforce the published edit_decisions JSON Schema.

    composition_validator only inspects assets/durations/overlaps; without this
    a misspelled optional field (transition instead of transition_in) validated
    clean and silently did nothing, and an illegal enum rendered anyway.
    """
    data = out.setdefault("data", {})
    try:
        document = json.loads(composition.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        data.setdefault("errors", []).append("Composition is not valid JSON: " + str(exc))
        out["success"] = False
        return
    if not _SCHEMA_PATH.is_file():
        data.setdefault("warnings", []).append(
            "schema 未找到（" + str(_SCHEMA_PATH) + "），跳过 schema 校验"
        )
        return
    try:
        from jsonschema import Draft202012Validator  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        data.setdefault("warnings", []).append("jsonschema 不可用，跳过 schema 校验")
        return
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = data.setdefault("errors", [])
    violations = sorted(
        Draft202012Validator(schema).iter_errors(document),
        key=lambda e: [str(p) for p in e.absolute_path],
    )
    for idx, err in enumerate(violations):
        if idx >= 12:
            errors.append("schema: 其余 " + str(len(violations) - 12) + " 条违反已省略")
            break
        where = "/".join(str(p) for p in err.absolute_path) or "<root>"
        errors.append("schema 违反 " + where + ": " + err.message)
    if violations:
        out["success"] = False


def _apply_narration_check(out: dict, composition: Path, assets_root) -> None:
    """Warn when narration runs past the picture (its tail gets cut silently)."""
    data = out.setdefault("data", {})
    try:
        doc = json.loads(composition.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return
    picture = 0.0
    for cut in doc.get("cuts") or []:
        if not isinstance(cut, dict) or cut.get("layer", "primary") != "primary":
            continue
        try:
            span = float(cut["out_seconds"]) - float(cut["in_seconds"])
            speed = float(cut.get("speed") or 1.0) or 1.0
        except (KeyError, TypeError, ValueError):
            return
        picture += span / speed
    if picture <= 0:
        return
    segments = ((doc.get("audio") or {}).get("narration") or {}).get("segments") or []
    for seg in segments:
        if not isinstance(seg, dict) or not seg.get("asset_id"):
            continue
        raw = seg["asset_id"]
        candidates = [Path(raw)]
        if assets_root:
            candidates.append(Path(assets_root) / raw)
        candidates.append(composition.parent / raw)
        path = next((c for c in candidates if c.is_file()), None)
        if path is None:
            continue
        duration = _duration_seconds(path)
        if duration <= 0:
            continue
        start = float(seg.get("start_seconds") or 0.0)
        if start + duration > picture + 0.1:
            data.setdefault("warnings", []).append(
                "旁白超出画面: " + path.name + " 到 " + format(start + duration, ".2f")
                + "s，画面只有 " + format(picture, ".2f") + "s，音尾会被截断"
            )


def cmd_validate(args) -> int:
    sys.path.insert(0, str(OM_HOME))
    from tools.analysis.composition_validator import CompositionValidator  # noqa: PLC0415

    inputs = {"composition_path": str(Path(args.composition).resolve())}
    if args.runtime:
        inputs["render_runtime"] = args.runtime
    if args.assets_root:
        inputs["assets_root"] = str(Path(args.assets_root).resolve())
    out = _tool_result(CompositionValidator().execute(inputs))
    _apply_schema_check(out, Path(args.composition).resolve())
    _apply_narration_check(out, Path(args.composition).resolve(), args.assets_root)
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print("PASS" if out["success"] else "FAIL")
        data = out["data"] or {}
        for key in ("errors", "warnings", "info"):
            for line in data.get(key) or []:
                print(f"  {key[:-1]}: {line}")
        if out["error"]:
            print(f"  error: {out['error']}")
    return 0 if out["success"] else 1


def cmd_compose(args) -> int:
    sys.path.insert(0, str(OM_HOME))
    from tools.video.video_compose import VideoCompose  # noqa: PLC0415

    edit = json.loads(Path(args.composition).read_text(encoding="utf-8"))
    inputs = {
        "operation": "compose",
        "edit_decisions": edit,
        "output_path": str(Path(args.out).resolve()),
        "codec": args.codec,
        "crf": args.crf,
        "preset": args.preset,
    }
    if args.audio:
        inputs["audio_path"] = str(Path(args.audio).resolve())
    # NOTE: do not forward --subs to video_compose. Its burn path builds a
    # `subtitles=` filter, and this machine's ffmpeg has no libass. Burn after
    # a clean render instead (see cmd_burn).
    burn_after = str(Path(args.subs).resolve()) if args.subs else None
    if args.profile:
        inputs["profile"] = args.profile
    out = _tool_result(VideoCompose().execute(inputs))
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print("OK" if out["success"] else "FAILED")
        data = out["data"] or {}
        for key in ("output_path", "duration_seconds", "resolution", "cut_count"):
            if key in data:
                print(f"  {key}: {data[key]}")
        if out["error"]:
            print(f"  error: {out['error']}")
    if not out["success"]:
        return 1
    if burn_after:
        print(f"  烧录字幕: {burn_after}")
        subs_block = edit.get("subtitles") or {}
        try:
            sub_size = int(subs_block.get("font_size") or 46)
        except (TypeError, ValueError):
            sub_size = 46
        ns = argparse.Namespace(
            video=str(Path(args.out).resolve()), srt=burn_after,
            out=str(Path(args.out).resolve()), font=None, size=sub_size, margin=72,
            ass_font="PingFang SC", ass_size=0, no_native=False,
            crf=args.crf, preset=args.preset,
            position=str(subs_block.get("position") or ""),
        )
        return cmd_burn(ns)
    return 0



def _has_filter(name: str) -> bool:
    try:
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-filters"],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError:
        return False
    return re.search(rf"^\s*\S+\s+{re.escape(name)}\s", proc.stdout, re.M) is not None


_POSITION_ALIGNMENT = {
    "top-center": 8,
    "top": 8,
    "center": 5,
    "middle": 5,
    "bottom-center": 2,
    "bottom": 2,
}


def _ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    sec = seconds - h * 3600 - m * 60
    return f"{h}:{m:02d}:{sec:05.2f}"


def _srt_to_ass(cues: list[dict], width: int, height: int, font: str, size: int,
                margin: int, alignment: int = 2) -> str:
    """Write a real ASS file so libass uses pixel sizes, not the 288-line default."""
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,2,0,{alignment},{margin},{margin},{margin},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for cue in cues:
        text = cue["text"].replace("\n", "\\N")
        lines.append(
            f"Dialogue: 0,{_ass_time(cue['start'])},{_ass_time(cue['end'])},Default,,0,0,0,,{text}"
        )
    return head + "\n".join(lines) + "\n"


def _burn_native(video: Path, srt: Path, out: Path, cue_list: list[dict], width: int,
                 height: int, font: str, size: int, margin: int,
                 crf: int, preset: str, alignment: int = 2) -> bool:
    """Native libass burn from a generated ASS file."""
    ass_path = out.parent / f".{out.stem}.ass"
    ass_path.write_text(
        _srt_to_ass(cue_list, width, height, font, size, margin, alignment),
        encoding="utf-8",
    )
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
        "-vf", f"subtitles=filename={ass_path.name}",
        "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
        "-pix_fmt", "yuv420p", "-c:a", "copy", str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False,
                          cwd=str(ass_path.parent))
    if proc.returncode != 0:
        print(f"  native burn failed: {proc.stderr.strip()[:300]}", file=sys.stderr)
        return False
    ass_path.unlink(missing_ok=True)
    return True


def cmd_mix(args) -> int:
    """Mix narration and music with side-chain ducking (music dips under voice)."""
    voice, music, out = Path(args.voice).resolve(), Path(args.music).resolve(), Path(args.out).resolve()
    for f in (voice, music):
        if not f.is_file():
            print(f"文件不存在: {f}", file=sys.stderr)
            return 2
    chain = (
        f"[1:a]volume={args.music_gain}[bgm];"
        f"[bgm][0:a]sidechaincompress=threshold={args.threshold}:ratio={args.ratio}"
        f":attack=5:release={args.release}[duck];"
        f"[0:a][duck]amix=inputs=2:duration=first:normalize=0[mix]"
    )
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(voice), "-i", str(music),
        "-filter_complex", chain, "-map", "[mix]", "-c:a", "aac", "-b:a", "192k",
        "-ar", "48000", str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        print(f"混音失败: {proc.stderr.strip()[:600]}", file=sys.stderr)
        return 1
    print(f"OK {out}")
    print(f"  人声 {voice.name} + 配乐 {music.name}（增益 {args.music_gain}，侧链压缩）")
    return 0


def cmd_attach(args) -> int:
    """Replace a video's audio track without re-encoding video."""
    video, audio = Path(args.video).resolve(), Path(args.audio).resolve()
    out = Path(args.out).resolve()
    for f in (video, audio):
        if not f.is_file():
            print(f"文件不存在: {f}", file=sys.stderr)
            return 2
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(audio),
           "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
           "-b:a", "192k", "-ar", "48000", "-shortest", str(out)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        print(f"换轨失败: {proc.stderr.strip()[:600]}", file=sys.stderr)
        return 1
    print(f"OK {out}")
    return 0


def _audio_codec_args(out: Path) -> list[str]:
    """Pick an audio encoder that matches the output container.

    Hard-coding aac wrote a nonstandard stream whenever the target was a .wav,
    which then failed to decode (decode_band_types) on the next pass.
    """
    ext = out.suffix.lower()
    if ext in (".wav", ".aif", ".aiff", ".caf"):
        return ["-c:a", "pcm_s16le", "-ar", "48000"]
    if ext == ".mp3":
        return ["-c:a", "libmp3lame", "-b:a", "192k", "-ar", "48000"]
    if ext == ".flac":
        return ["-c:a", "flac", "-ar", "48000"]
    return ["-c:a", "aac", "-b:a", "192k", "-ar", "48000"]


def cmd_norm(args) -> int:
    """Two-pass EBU R128 loudness normalisation."""
    src, out = Path(args.input).resolve(), Path(args.out).resolve()
    if not src.is_file():
        print(f"文件不存在: {src}", file=sys.stderr)
        return 2
    target = f"I={args.lufs}:TP={args.tp}:LRA={args.lra}"
    probe_cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", str(src),
                 "-af", f"loudnorm={target}:print_format=json", "-f", "null", "-"]
    proc = subprocess.run(probe_cmd, capture_output=True, text=True, check=False)
    measured = {}
    match = re.search(r'\{[^{}]*"input_i"[^{}]*\}', proc.stderr, re.S)
    if match:
        try:
            measured = json.loads(match.group(0))
        except json.JSONDecodeError:
            measured = {}
    filters = f"loudnorm={target}"
    if measured:
        filters += (
            f":measured_I={measured.get('input_i')}"
            f":measured_TP={measured.get('input_tp')}"
            f":measured_LRA={measured.get('input_lra')}"
            f":measured_thresh={measured.get('input_thresh')}"
            f":offset={measured.get('target_offset')}:linear=true"
        )
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
           "-af", filters, "-c:v", "copy", *_audio_codec_args(out), str(out)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        print(f"响度归一失败: {proc.stderr.strip()[:600]}", file=sys.stderr)
        return 1
    print(f"OK {out}")
    src_i = measured.get("input_i") if measured else "?"
    print(f"  目标 {args.lufs} LUFS / TP {args.tp} dB  原响度 {src_i} LUFS")
    return 0


def _ffprobe(path: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "ffprobe failed")
    return json.loads(proc.stdout)


def _fps(stream: dict) -> float:
    raw = stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "0/1"
    try:
        num, den = raw.split("/")
        return round(float(num) / float(den), 3) if float(den) else 0.0
    except (ValueError, ZeroDivisionError):
        return 0.0


def _measure_loudness(path: Path) -> dict:
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
        capture_output=True, text=True, check=False,
    )
    out = {"integrated": None, "peak": None}
    for line in proc.stderr.splitlines():
        line = line.strip()
        if line.startswith("I:") and "LUFS" in line:
            out["integrated"] = float(line.split()[1])
        elif line.startswith("Peak:") and "dBFS" in line:
            out["peak"] = float(line.split()[1])
    return out


def cmd_probe(args) -> int:
    path = Path(args.media).resolve()
    if not path.is_file():
        print(f"文件不存在: {path}", file=sys.stderr)
        return 2
    info = _ffprobe(path)
    fmt = info.get("format") or {}
    streams = info.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    summary = {
        "path": str(path),
        "duration": round(float(fmt.get("duration") or 0), 3),
        "size_bytes": int(fmt.get("size") or path.stat().st_size),
        "bit_rate": int(fmt.get("bit_rate") or 0),
        "video": None if not video else {
            "codec": video.get("codec_name"),
            "width": video.get("width"),
            "height": video.get("height"),
            "fps": _fps(video),
            "pix_fmt": video.get("pix_fmt"),
            "frames": video.get("nb_frames"),
        },
        "audio": [
            {
                "codec": s.get("codec_name"),
                "sample_rate": int(s.get("sample_rate") or 0),
                "channels": s.get("channels"),
            }
            for s in audios
        ],
    }

    if args.loudness:
        summary["loudness"] = _measure_loudness(path)

    failures: list[str] = []
    for raw in args.expect or []:
        if "=" not in raw:
            failures.append(f"断言格式应为 key=value: {raw}")
            continue
        key, want = raw.split("=", 1)
        key = key.strip().lower()
        got = None
        if key == "width" and summary["video"]:
            got = summary["video"]["width"]
        elif key == "height" and summary["video"]:
            got = summary["video"]["height"]
        elif key == "fps" and summary["video"]:
            got = summary["video"]["fps"]
        elif key == "duration":
            got = summary["duration"]
        elif key == "vcodec" and summary["video"]:
            got = summary["video"]["codec"]
        elif key == "pix_fmt" and summary["video"]:
            got = summary["video"]["pix_fmt"]
        elif key == "audio":
            got = "yes" if summary["audio"] else "no"
        elif key == "lufs" and summary.get("loudness", {}).get("integrated") is not None:
            got = summary["loudness"]["integrated"]
        elif key == "acodec":
            got = summary["audio"][0]["codec"] if summary["audio"] else None
        if got is None:
            failures.append(f"{key}: 媒体里没有该字段")
            continue
        if key in ("duration", "fps", "lufs"):
            try:
                tol = {"duration": 0.2, "fps": 0.05, "lufs": 1.0}[key]
                ok = abs(float(got) - float(want)) <= tol
            except ValueError:
                ok = str(got) == want
        else:
            ok = str(got) == want
        if not ok:
            failures.append(f"{key}: 期望 {want}，实际 {got}")

    summary["assertions"] = {"checked": len(args.expect or []), "failures": failures}
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"{summary['path']}")
        print(f"  时长 {summary['duration']}s  体积 {summary['size_bytes']}B")
        if summary["video"]:
            v = summary["video"]
            print(f"  视频 {v['codec']} {v['width']}x{v['height']} {v['fps']}fps {v['pix_fmt']}")
        print(f"  音轨 {len(summary['audio'])} 条" + (
            f" ({summary['audio'][0]['codec']} {summary['audio'][0]['sample_rate']}Hz)"
            if summary["audio"] else ""))
        if summary.get("loudness", {}).get("integrated") is not None:
            print(f"  响度 {summary['loudness']['integrated']} LUFS")
        if failures:
            for line in failures:
                print(f"  ASSERT FAIL {line}")
        elif args.expect:
            print("  断言全部通过")
    return 0 if not failures else 1



SRT_TIME = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
)
FONT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
]


def _parse_srt(text: str) -> list[dict]:
    cues: list[dict] = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [ln.rstrip() for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        match = SRT_TIME.search(lines[1] if SRT_TIME.search(lines[1]) else lines[0])
        if not match:
            continue
        g = [int(x) for x in match.groups()]
        start = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        end = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        body = "\n".join(lines[2:]) if SRT_TIME.search(lines[1]) else "\n".join(lines[1:])
        if body.strip():
            cues.append({"start": start, "end": end, "text": body.strip()})
    return cues


def _render_cue_png(text: str, width: int, height: int, font_path: str, size: int,
                    margin: int, out: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont  # noqa: PLC0415

    font = ImageFont.truetype(font_path, size)
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    max_w = width - 2 * margin
    lines: list[str] = []
    for para in text.split("\n"):
        cur = ""
        for ch in para:
            probe = cur + ch
            if draw.textlength(probe, font=font) <= max_w:
                cur = probe
            else:
                if cur:
                    lines.append(cur)
                cur = ch
        lines.append(cur)
    line_h = int(size * 1.32)
    total_h = line_h * len(lines)
    y = height - margin - total_h
    for line in lines:
        w = draw.textlength(line, font=font)
        x = (width - w) / 2
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0, 230))
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += line_h
    img.save(out)


def cmd_burn(args) -> int:
    """Hard-burn SRT via PIL overlays.

    The local ffmpeg build has no libass, so ``subtitles``/``ass``/``drawtext``
    are unavailable. Rendering cue PNGs and compositing them with the
    ``overlay`` filter keeps hard subtitles working without a new toolchain.
    """
    video = Path(args.video).resolve()
    srt = Path(args.srt).resolve()
    out = Path(args.out).resolve()
    if not video.is_file() or not srt.is_file():
        print("视频或字幕文件不存在", file=sys.stderr)
        return 2
    cues = _parse_srt(srt.read_text(encoding="utf-8"))
    if not cues:
        print("字幕里没有可用条目", file=sys.stderr)
        return 2
    info = _ffprobe(video)
    video_stream = next(s for s in info["streams"] if s.get("codec_type") == "video")
    width, height = int(video_stream["width"]), int(video_stream["height"])
    font_path = args.font
    if not font_path:
        font_path = next((f for f in FONT_CANDIDATES if Path(f).is_file()), "")
    if not font_path:
        print("找不到可用中文字体，用 --font 指定", file=sys.stderr)
        return 2

    tmp_out = out.with_name(f".{out.stem}.burn{out.suffix}")

    alignment = _POSITION_ALIGNMENT.get(
        str(getattr(args, "position", "") or "").strip().lower(), 2
    )
    if not args.no_native and _has_filter("subtitles"):
        if _burn_native(video, srt, tmp_out, cues, width, height, args.ass_font,
                        args.size, args.margin, args.crf, args.preset, alignment):
            os.replace(tmp_out, out)
            print(f"OK {out}")
            print(f"  字幕 {len(cues)} 条  模式 libass 原生（字号 {args.size}px）")
            return 0
        print("  回退到 PIL 叠加", file=sys.stderr)

    tmp = Path(out).parent / ".burn_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    duration = float((info.get("format") or {}).get("duration") or 0)
    fps = _fps(video_stream) or 30.0

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video)]
    for idx, cue in enumerate(cues, start=1):
        png = tmp / f"cue_{idx:03d}.png"
        _render_cue_png(cue["text"], width, height, font_path, args.size, args.margin, png)
        cmd += ["-loop", "1", "-t", f"{max(duration, cue['end']):.3f}", "-i", str(png)]
    chains = []
    prev = "0:v"
    for idx, cue in enumerate(cues, start=1):
        label = f"v{idx}"
        chains.append(
            f"[{prev}][{idx}:v]overlay=0:0:enable='between(t,{cue['start']:.3f},{cue['end']:.3f})'[{label}]"
        )
        prev = label
    cmd += ["-filter_complex", ";".join(chains), "-map", f"[{prev}]",
            "-map", "0:a?", "-c:v", "libx264", "-crf", str(args.crf),
            "-preset", args.preset, "-pix_fmt", "yuv420p",
            "-r", f"{fps:.3f}", "-t", f"{duration:.3f}", "-shortest",
            "-c:a", "copy", str(tmp_out)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        print(f"烧录失败: {proc.stderr.strip()[:800]}", file=sys.stderr)
        return 1
    os.replace(tmp_out, out)
    print(f"OK {out}")
    print(f"  字幕 {len(cues)} 条  字体 {Path(font_path).name}")
    return 0


def cmd_remotion(args) -> int:
    """Render a Remotion composition from remotion-composer with a props file."""
    composer = OM_HOME / "remotion-composer"
    cli = composer / "node_modules/@remotion/cli/remotion-cli.js"
    if not cli.is_file():
        print(f"Remotion 未安装: {cli}", file=sys.stderr)
        return 2
    props = Path(args.props).resolve() if args.props else None
    if props and not props.is_file():
        print(f"props 不存在: {props}", file=sys.stderr)
        return 2
    cmd = ["node", str(cli), "render", str(composer / "src/index.tsx"), args.composition,
           str(Path(args.out).resolve()), "--log=error"]
    if props:
        cmd.append(f"--props={props}")
    if args.scale:
        cmd.append(f"--scale={args.scale}")
    if args.frames:
        cmd.append(f"--frames={args.frames}")
    public_dir = getattr(args, "public_dir", None)
    if public_dir:
        resolved_public = Path(public_dir).resolve()
        if not resolved_public.is_dir():
            print(f"public 目录不存在: {resolved_public}", file=sys.stderr)
            return 2
        cmd.append(f"--public-dir={resolved_public}")
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=str(composer))
    if proc.returncode != 0:
        print(f"渲染失败: {(proc.stderr or proc.stdout).strip()[:800]}", file=sys.stderr)
        return 1
    print(f"OK {Path(args.out).resolve()}")
    return 0


def cmd_doctor(args) -> int:
    checks = []
    checks.append(("repo", OM_HOME.is_dir(), str(OM_HOME)))
    checks.append(("venv", (OM_HOME / ".venv/bin/python").exists(), str(OM_HOME / ".venv")))
    checks.append(("ffmpeg", shutil.which("ffmpeg") is not None, shutil.which("ffmpeg") or "-"))
    checks.append(("ffprobe", shutil.which("ffprobe") is not None, shutil.which("ffprobe") or "-"))
    checks.append(("pipelines", (OM_HOME / "pipeline_defs").is_dir(), "pipeline_defs"))
    checks.append(("schemas", (OM_HOME / "schemas/artifacts").is_dir(), "schemas/artifacts"))
    remotion_cli = OM_HOME / "remotion-composer/node_modules/@remotion/cli/remotion-cli.js"
    checks.append(("remotion", remotion_cli.is_file(), str(remotion_cli.parent.parent)))
    checks.append(("node", shutil.which("node") is not None, shutil.which("node") or "-"))
    for filt in ("subtitles", "ass", "drawtext", "loudnorm", "ebur128", "sidechaincompress"):
        checks.append((f"filter:{filt}", _has_filter(filt), "ffmpeg -filters"))
    try:
        sys.path.insert(0, str(OM_HOME))
        from tools.analysis.composition_validator import CompositionValidator  # noqa: PLC0415,F401

        checks.append(("import", True, "composition_validator"))
    except Exception as exc:  # noqa: BLE001
        checks.append(("import", False, str(exc)))
    ok = True
    for name, passed, detail in checks:
        ok = ok and passed
        print(f"{'ok  ' if passed else 'FAIL'} {name:10s} {detail}")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="om", description="OpenMontage bridge for the DSH media preset")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("pipelines", help="列出管道清单")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_pipelines)

    p = sub.add_parser("skills", help="列出阶段指南路径")
    p.add_argument("pipeline", nargs="?")
    p.add_argument("--show", nargs="?", const=4000, type=int, default=0)
    p.set_defaults(func=cmd_skills)

    p = sub.add_parser("validate", help="校验 composition JSON")
    p.add_argument("composition")
    p.add_argument("--runtime", choices=["ffmpeg", "remotion", "hyperframes"])
    p.add_argument("--assets-root")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("compose", help="按编辑决策渲染成片")
    p.add_argument("composition")
    p.add_argument("--out", required=True)
    p.add_argument("--audio")
    p.add_argument("--subs")
    p.add_argument("--profile")
    p.add_argument("--codec", default="libx264")
    p.add_argument("--crf", type=int, default=20)
    p.add_argument("--preset", default="medium")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_compose)

    p = sub.add_parser("probe", help="ffprobe 摘要与断言")
    p.add_argument("media")
    p.add_argument("--loudness", action="store_true", help="用 ebur128 测集成响度")
    p.add_argument("--expect", action="append", metavar="KEY=VALUE")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_probe)

    p = sub.add_parser("burn", help="硬字幕烧录（PIL 叠加，无需 libass）")
    p.add_argument("video")
    p.add_argument("--srt", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--font")
    p.add_argument("--ass-font", default="PingFang SC")
    p.add_argument("--ass-size", type=int, default=0)
    p.add_argument("--no-native", action="store_true")
    p.add_argument("--size", type=int, default=46)
    p.add_argument("--margin", type=int, default=72)
    p.add_argument("--crf", type=int, default=20)
    p.add_argument("--preset", default="medium")
    p.add_argument("--position", default="", help="top-center|center|bottom-center")
    p.set_defaults(func=cmd_burn)

    p = sub.add_parser("mix", help="人声与配乐侧链混音")
    p.add_argument("--voice", required=True)
    p.add_argument("--music", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--music-gain", default="0.28")
    p.add_argument("--threshold", default="0.03")
    p.add_argument("--ratio", default="8")
    p.add_argument("--release", default="350")
    p.set_defaults(func=cmd_mix)

    p = sub.add_parser("attach", help="用新音轨替换视频音轨，视频不重编码")
    p.add_argument("--video", required=True)
    p.add_argument("--audio", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_attach)

    p = sub.add_parser("norm", help="EBU R128 响度归一（两遍）")
    p.add_argument("input")
    p.add_argument("--out", required=True)
    p.add_argument("--lufs", default="-14")
    p.add_argument("--tp", default="-1.5")
    p.add_argument("--lra", default="11")
    p.set_defaults(func=cmd_norm)

    p = sub.add_parser("remotion", help="用 Remotion 渲染动效/图文成片")
    p.add_argument("composition")
    p.add_argument("--out", required=True)
    p.add_argument("--props")
    p.add_argument("--scale")
    p.add_argument("--frames")
    p.add_argument("--public-dir", help="Remotion public 目录（绝对路径素材需放这里）")
    p.set_defaults(func=cmd_remotion)

    p = sub.add_parser("doctor", help="环境自检")
    p.set_defaults(func=cmd_doctor)
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "doctor" and not OM_HOME.is_dir():
        print(f"找不到 OpenMontage: {OM_HOME}（设置 OPENMONTAGE_HOME 指向仓库）", file=sys.stderr)
        return 2
    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # noqa: BLE001
        print(f"失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))