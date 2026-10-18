"""Local JSON contract demonstration. Does not transmit data to any service."""
from pathlib import Path
import argparse
import json
from interface import initialize, process, AS_OF

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('payload',type=Path)
    parser.add_argument('--db',type=Path,default=ROOT/'runtime'/'demo.db')
    args=parser.parse_args()
    initialize(args.db)
    result=process(args.db,args.payload.read_text(encoding='utf-8'),AS_OF)
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['http_status']<400 else 1)


if __name__=='__main__':
    main()
