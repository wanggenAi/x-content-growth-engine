"""CLI for small hourly briefs and private verbatim notes."""
import argparse
from .observer import build_digest, save_note

def main(argv=None):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    d = sub.add_parser("digest")
    d.add_argument("--config", default="config/sources.json")
    d.add_argument("--out", default="reports/hourly")
    d.add_argument("--state", default="state/seen.json")
    n = sub.add_parser("note")
    n.add_argument("--text", required=True)
    n.add_argument("--kind", choices=("personal","seen","thought"), default="personal")
    n.add_argument("--out", default="journal")
    a = p.parse_args(argv)
    if a.command == "digest":
        print(build_digest(a.config, a.out, a.state)["markdown"])
    else:
        print(save_note(a.text, a.kind, a.out))

if __name__ == "__main__":
    main()
