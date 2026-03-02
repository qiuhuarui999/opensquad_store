"""
build_zips.py
将每个技能子目录打包为 {id}.zip，zip 内文件无前缀目录，直接是 SKILL.md + tools.py
运行方式：python build_zips.py
输出：skills/ 目录下生成 code_reviewer_lite.zip / api_tester.zip / git_helper.zip
"""
import os
import zipfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

SKILL_IDS = ["code_reviewer_lite", "api_tester", "git_helper"]

for skill_id in SKILL_IDS:
    skill_dir = os.path.join(SCRIPT_DIR, skill_id)
    zip_path = os.path.join(SCRIPT_DIR, f"{skill_id}.zip")

    if not os.path.isdir(skill_dir):
        print(f"[SKIP] 目录不存在: {skill_dir}")
        continue

    files_to_pack = []
    for fname in ["SKILL.md", "tools.py"]:
        fpath = os.path.join(skill_dir, fname)
        if os.path.isfile(fpath):
            files_to_pack.append((fpath, fname))
        else:
            print(f"[WARN] 文件缺失: {fpath}")

    if not files_to_pack:
        print(f"[SKIP] {skill_id}: 无文件可打包")
        continue

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fpath, arcname in files_to_pack:
            zf.write(fpath, arcname)
            print(f"  + {arcname}")

    print(f"[OK] {skill_id}.zip 已生成 -> {zip_path}")

print("全部完成。")
