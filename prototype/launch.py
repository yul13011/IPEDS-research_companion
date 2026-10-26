"""Bootstrap project-local packages without modifying the shared Python runtime."""
from pathlib import Path
import sys

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
if (root/'.packages').exists():sys.path.insert(0,str(root/'.packages'))
from streamlit.web.cli import main
sys.argv=['streamlit','run',str(root/'prototype/app.py'),*sys.argv[1:]]
if __name__=='__main__':main()
