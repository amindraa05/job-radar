"""Perbaiki NOT_INFRA: kembalikan batas kata yang hilang saat penulisan."""
import pathlib
import re

p = pathlib.Path(__file__).resolve().parent / "match.py"
s = p.read_text(encoding="utf-8")

mulai = s.index("NOT_INFRA = re.compile(")
akhir = s.index(")", s.index('|game|graphic|recruit|teacher|nurse"')) + 1

baru = '''NOT_INFRA = re.compile(
    r"\\bphysical security\\b|\\bsecurity systems\\b|\\bfire alarm\\b"
    r"|\\bcustomer (success|solutions?)\\b|\\bsolutions? consultant\\b"
    r"|\\bpre-?sales\\b|\\bsales engineer\\b|\\baccount (executive|manager)\\b"
    r"|\\bfield (engineer|technician)\\b|\\bmechanical\\b|\\belectrical\\b"
    r"|\\bmanufacturing\\b|\\bhardware design\\b|\\bfirmware\\b|\\bsilicon\\b"
    r"|\\bqa engineer\\b|\\btest engineer\\b|\\bdata (scientist|analyst)\\b"
    r"|\\bmachine learning engineer\\b|\\bresearch (scientist|engineer)\\b"
    r"|\\bfront-?end\\b|\\bmobile\\b|\\bios\\b|\\bandroid\\b|\\bgame\\b"
    r"|\\bgraphic\\b|\\brecruit\\w*\\b|\\bteacher\\b|\\bnurse\\b|\\bmarketing\\b"
)'''

s = s[:mulai] + baru + s[akhir:]
p.write_text(s, encoding="utf-8")

# buktikan batas kata benar-benar ada dan tidak salah tangkap
import importlib
import sys
sys.path.insert(0, str(p.parent))
if "match" in sys.modules:
    del sys.modules["match"]
import match  # noqa: E402

UJI_TOLAK = ["Physical Security Systems Engineer - APAC",
             "Customer Solutions Architect", "Sales Engineer, Cloud",
             "iOS Engineer", "QA Engineer", "Marketing Manager"]
UJI_TERIMA = ["Site Reliability Engineer", "Cloud Infrastructure Engineer",
              "Systems Engineer, Production", "DevOps Engineer",
              "Various Systems Engineer", "Scenarios Platform Engineer",
              "Linux Systems Administrator"]

print("harus DITOLAK:")
for t in UJI_TOLAK:
    r, _ = match.classify_role(t)
    print(f"  {'ok ' if r is None else 'GAGAL'}  {t}  -> {r}")
print("harus DITERIMA:")
for t in UJI_TERIMA:
    r, _ = match.classify_role(t)
    print(f"  {'ok ' if r else 'GAGAL'}  {t}  -> {r}")
