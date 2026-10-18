"""The app's server with the P4 spike route, for the browser pane.

  python spikes/chat-2026-10-18/spike_server.py --port 8799 --data-dir DIR --log FILE
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE)]
from app import server  # noqa: E402
import spike_routes  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, required=True)
parser.add_argument('--data-dir', type=Path, required=True)
parser.add_argument('--log', type=Path, required=True)
args = parser.parse_args()
spike_routes.install(server.Handler, args.log)
sys.argv = [sys.argv[0], '--port', str(args.port), '--data-dir', str(args.data_dir)]
server.main()
