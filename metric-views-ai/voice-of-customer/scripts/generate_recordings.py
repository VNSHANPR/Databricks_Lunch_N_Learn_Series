#!/usr/bin/env python3
"""
Generate a handful of simulated contact-centre call recordings for the
Voice-of-Customer lab — the "Brickstage recorder lands WAVs in a Volume" scenario.

Each call is synthesised with macOS `say` (one voice per speaker so it sounds like a
real agent<->customer conversation), converted to 16 kHz mono PCM WAV with `afconvert`
(the format ai_transcribe expects), and the turns are concatenated into one WAV per call
with `ffmpeg`. We also emit:
  - data/conversations.csv          call metadata (joined in Gold; NO reason label)
  - data/ground_truth.csv           full transcript + true call reason (fallback + WER ref)

Run locally on a Mac:  python3 scripts/generate_recordings.py
(Only needs the macOS built-ins `say`/`afconvert` + `ffmpeg` on PATH.)
"""
from __future__ import annotations
import csv, json, os, subprocess, sys, tempfile
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = (HERE.parent / "data")
REC_DIR = DATA / "recordings"

# Call-reason taxonomy the Gold layer's ai_classify will choose from.
LABELS = ["new_booking_enquiry", "booking_change", "cancellation", "refund_request",
          "payment_issue", "delay_or_disruption", "loyalty_points", "complaint",
          "compliment", "other"]

# Six scripted HTG travel calls (speaker, line). `reason` is ground truth for the demo.
CALLS = [
    dict(call_id="CALL-0001", reason="refund_request", queue="Leisure Support", agent="Priya Sharma",
         agent_id="A-204", customer_id="C-88213",
         turns=[("agent", "Thanks for calling HTG Travel, this is Priya. How can I help today?"),
                ("customer", "Hi Priya. My Bali package was cancelled by the operator and I still haven't received my refund. It's been three weeks."),
                ("agent", "I'm sorry about that. Let me pull up the booking. I can see the cancellation here — I'll escalate the refund and you should see it within five business days."),
                ("customer", "Okay, thank you. Three weeks was far too long to wait though."),
                ("agent", "Completely understand, I've flagged it as a priority. You'll get an email confirmation shortly.")]),
    dict(call_id="CALL-0002", reason="booking_change", queue="Leisure Support", agent="Daniel Lee",
         agent_id="A-118", customer_id="C-45190",
         turns=[("agent", "Good afternoon, HTG Travel, Daniel speaking."),
                ("customer", "Hi, I need to move my flights to Tokyo from the twelfth of June to the nineteenth. Is that possible?"),
                ("agent", "Let me check availability. Yes, there's space on the nineteenth. There's a small change fee and a fare difference of about ninety dollars."),
                ("customer", "That's fine, please go ahead and change it."),
                ("agent", "Done. Your new itinerary is confirmed for the nineteenth and I've emailed the updated tickets.")]),
    dict(call_id="CALL-0003", reason="delay_or_disruption", queue="Urgent Assist", agent="Karen Mitchell",
         agent_id="A-307", customer_id="C-77654",
         turns=[("customer", "This is an absolute mess. My connecting flight in Singapore was cancelled and I'm stuck at the airport."),
                ("agent", "I'm really sorry you're stuck. Let me find you the next available connection right now."),
                ("customer", "I've been waiting six hours with two kids. This is unacceptable."),
                ("agent", "I hear you. I've rebooked you on the next flight in ninety minutes and arranged lounge access for your family. I'll text the details now."),
                ("customer", "Alright, thank you for sorting it quickly at least.")]),
    dict(call_id="CALL-0004", reason="new_booking_enquiry", queue="New Sales", agent="Tom Nguyen",
         agent_id="A-512", customer_id="C-10022",
         turns=[("agent", "HTG Travel, Tom here, how can I help?"),
                ("customer", "Hi, I'm thinking about a South Pacific cruise for two in September. What options do you have?"),
                ("agent", "Great timing — we have a ten-night Fiji and Vanuatu cruise with an early-bird deal. Shall I email you a few packages with pricing?"),
                ("customer", "Yes please, that sounds perfect. No need to book yet, just send the options."),
                ("agent", "No problem, I'll send three options this afternoon.")]),
    dict(call_id="CALL-0005", reason="loyalty_points", queue="Member Services", agent="Aisha Khan",
         agent_id="A-260", customer_id="C-33771",
         turns=[("agent", "Welcome to HTG Member Services, this is Aisha."),
                ("customer", "Hi, I'm a Gold member and I'd like to use my points towards a hotel booking in Queenstown."),
                ("agent", "Of course. You have forty-two thousand points, which covers about two nights. Would you like me to apply them?"),
                ("customer", "Yes, apply them to the booking please."),
                ("agent", "Applied. Your points balance and the updated booking are now in your account.")]),
    dict(call_id="CALL-0006", reason="compliment", queue="Leisure Support", agent="Priya Sharma",
         agent_id="A-204", customer_id="C-60918",
         turns=[("customer", "Hi, I just wanted to call and say the consultant who booked our honeymoon was fantastic."),
                ("agent", "That's lovely to hear, thank you so much. I'll pass that on to the team."),
                ("customer", "Everything was seamless, the upgrades were a wonderful surprise. We'll definitely book with HTG again."),
                ("agent", "We really appreciate you taking the time to call. Welcome back any time!")]),
]

# Prefer Australian/UK voices; fall back to whatever is installed.
AGENT_PREFS = ["Daniel", "Lee", "Oliver", "Alex", "Fred"]
CUSTOMER_PREFS = ["Karen", "Catherine", "Serena", "Samantha", "Victoria", "Moira"]


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def installed_voices() -> set[str]:
    out = subprocess.run(["say", "-v", "?"], capture_output=True, text=True).stdout
    return {line.split()[0] for line in out.splitlines() if line.strip()}


def pick(prefs: list[str], installed: set[str]) -> str | None:
    for v in prefs:
        if v in installed:
            return v
    return None  # None → system default voice


def synth_turn(text: str, voice: str | None, out_wav: Path, tmp: Path) -> None:
    aiff = tmp / "turn.aiff"
    say_cmd = ["say", "-r", "180", "-o", str(aiff)]
    if voice:
        say_cmd += ["-v", voice]
    say_cmd += [text]
    run(say_cmd)
    # 16 kHz, mono, signed 16-bit PCM WAV — the shape ai_transcribe is happy with.
    run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", str(aiff), str(out_wav)])


def build_call(call: dict, agent_voice, customer_voice) -> int:
    REC_DIR.mkdir(parents=True, exist_ok=True)
    out_wav = REC_DIR / f"{call['call_id'].lower().replace('-', '_')}.wav"
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        turn_files = []
        for i, (speaker, line) in enumerate(call["turns"]):
            tw = tmp / f"turn_{i:02d}.wav"
            synth_turn(line, agent_voice if speaker == "agent" else customer_voice, tw, tmp)
            turn_files.append(tw)
        listfile = tmp / "list.txt"
        listfile.write_text("".join(f"file '{p}'\n" for p in turn_files))
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
             "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(out_wav)])
    return out_wav.stat().st_size


def main() -> int:
    voices = installed_voices()
    agent_voice, customer_voice = pick(AGENT_PREFS, voices), pick(CUSTOMER_PREFS, voices)
    print(f"Agent voice: {agent_voice or 'system default'} | Customer voice: {customer_voice or 'system default'}")

    DATA.mkdir(parents=True, exist_ok=True)
    base_ts = datetime(2026, 11, 14, 9, 5, 0)
    conv_rows, truth_rows = [], []
    for n, call in enumerate(CALLS):
        size = build_call(call, agent_voice, customer_voice)
        audio_file = f"{call['call_id'].lower().replace('-', '_')}.wav"
        start = base_ts + timedelta(minutes=37 * n)
        duration = 45 + 12 * len(call["turns"])  # rough, seconds
        conv_rows.append(dict(call_id=call["call_id"], audio_file=audio_file, agent_id=call["agent_id"],
                              agent_name=call["agent"], queue=call["queue"], channel="Phone",
                              call_start_ts=start.isoformat(sep=" "), duration_seconds=duration,
                              customer_id=call["customer_id"]))
        truth_rows.append(dict(call_id=call["call_id"], audio_file=audio_file,
                               ground_truth_reason=call["reason"],
                               transcript=" ".join(line for _, line in call["turns"])))
        print(f"  {audio_file}  ({size/1024:.0f} KB, reason={call['reason']})")

    with (DATA / "conversations.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(conv_rows[0].keys())); w.writeheader(); w.writerows(conv_rows)
    with (DATA / "ground_truth.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(truth_rows[0].keys())); w.writeheader(); w.writerows(truth_rows)
    (DATA / "labels.json").write_text(json.dumps(LABELS, indent=2))
    print(f"\nWrote {len(CALLS)} WAVs to {REC_DIR}")
    print(f"Wrote conversations.csv, ground_truth.csv, labels.json to {DATA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
