#!/usr/bin/env python3
"""Package only a completed, independently audited v2 batch. No model calls."""
from pathlib import Path
from datetime import datetime, timezone
import csv, hashlib, json, zipfile, importlib.metadata
R = Path(__file__).resolve().parents[1]
def read(p): return json.loads((R / p).read_text())
def sha(b): return hashlib.sha256(b).hexdigest()
def main():
 s = read('analysis/dev/summary.json')
 assert s['planned_tasks'] == 800 and s['passed_integrity']
 assert sum(s['status_counts'].values()) == 800
 assert not set(s['status_counts']) & {'not_executed','paused_unfinalized'}
 a = read('audits/INDEPENDENT_FINAL_AUDIT.json')
 assert a['audit_status'] == 'completed' and a['deterministic_integrity'] == 'PASS'
 # Bind publication to the exact independently reviewed inputs and outputs.
 for rel,digest in a['audited_input_hashes'].items():
  assert sha((R/rel).read_bytes()) == digest, ('audited input drift',rel)
 for base,filename,key in [('report','report_manifest.json','output_sha256'),('figures','figure_manifest.json','outputs')]:
  provenance = read(base+'/'+filename)
  for rel,digest in provenance['input_sha256'].items():
   assert sha((R/rel).read_bytes()) == digest, ('presentation input drift',rel)
  for rel,digest in provenance[key].items():
   assert sha((R/base/rel).read_bytes()) == digest, ('presentation output drift',rel)
 assert read('figures/figure_manifest.json')['visual_review'] == 'passed'
 assert read('audits/viewer_check.json')['passed']
 assert (R/'report/DEV_REPORT.md').is_file()
 p0=s['procedures']['P0']; freeze=sha((R/'protocol/frozen.json').read_bytes())
 (R/'README_中文.md').write_text(f'''# Codex 核验机制 v2：固定 800 任务开发实验

8 个合成案例家族（4 材料适用性、4 条款条件），80 题、每题 2 次首轮重复、5 种程序。全部 800 个计划任务已有终态；其中成功完成 {s['complete_tasks']}，实际 CLI 尝试 {s['actual_cli_attempts']}。请求模型 gpt-6-astra / ultra；没有真人被试、没有 DeepSeek 新调用。

- [中文报告](report/DEV_REPORT.md)：结果、解释、失败与资源范围。
- [离线回放](viewer.html)：80 题 × 2 次重复，各含共享首轮及4种复核。
- [科研图](figures/)：设计、家族正确率、对比与实际任务资源（SVG/PNG/PDF）。
- [评分数据](analysis/dev/)：[原始记录](runs/dev/)；不修改或重新抽取已有回答。
- [执行前修订](protocol/EXECUTION_AMENDMENT.md)：固定800，160首轮只是描述性诊断，没有另外筛查或结果驱动选题。
- [执行中并发修订](protocol/CONCURRENCY_AMENDMENT_2026-11-07.json)：用户授权在667次完成后，将剩余133次从3并发提高至12；6并发未运行。原冻结输入和既有答案保持原样；时间资源统计混合两个并发阶段，不能用于因果性提速比较。
- [题库规范](cases/CASE_SPEC.md)、[内部盲审](audits/case_review.json)、[工具链预审](audits/PREFLIGHT_REVIEW.md)。
- [独立最终复算](audits/INDEPENDENT_FINAL_AUDIT.json)：内部同模型家族审查，非外部教育专家验证。

P0 正确率 {p0['correct']}/{p0['planned']}。纠错率分母为零时为 NA，不是零效果；天花板不能证明方法等价或机制优势。重复调用、题目变体与建议方向不是独立人类或独立家族。每类仅4个构造家族，结果仅是 simulation_only 开发性描述。

## 归档复算（不调用模型）

在明确下载的完整归档目录中可运行：

```bash
python audits/independent_final_audit.py --archive-root /绝对/归档路径 --final
```

独立复算脚本仅用 Python 标准库，核对归档的内容哈希、原始记录和统计，不需要原 CLI。它只证明这份归档证据的一致性，不声称在原电脑重新运行了实验。

原主机、原绝对路径以及原 CLI 二进制完全匹配时，可运行 `python harness/runner.py --verify` 和 `python harness/evaluate.py dev`。runner/evaluator 的严格身份检查故意拒绝把副本或不同环境当成原任务恢复；不要修改 frozen.json 来绕过检查。模型执行入口是 `--phase dev`，不要与只读复算混淆。

冻结SHA-256：`{freeze}`。`FILE_MANIFEST.csv` 为本次归档文件清单；排除缓存、空运行目录、临时文件和进程锁。本地 ZIP 位于本目录上一级，GitHub只提交解包研究文件，避免重复存储。

原始日志保留执行时路径、会话ID和原始字节。这里的计量仅涵盖被试任务，作者、内部审阅及协调开销完整用量未知；费用为NA。没有独立教育专家、真实学校参与者、保留集或跨模型确认。
''')
 (R/'requirements-runtime.txt').write_text('\n'.join(f'{n}=={importlib.metadata.version(n)}' for n in ['jsonschema','numpy','matplotlib'])+'\n# Actual installed distributions, not a cross-platform lockfile.\n')
 files=[]
 for p in sorted(R.rglob('*')):
  if not p.is_file() or any(x in p.parts for x in ['__pycache__','runtime_empty']): continue
  if p.name in ['FILE_MANIFEST.csv','ZIP_PACKAGING.json','.integrity.lock','.lock'] or p.suffix in ['.tmp','.pyc','.zip']: continue
  files.append(p)
 manifest=R/'FILE_MANIFEST.csv'
 with manifest.open('w',newline='') as h:
  w=csv.writer(h);w.writerow(['path','bytes','sha256'])
  for p in files:
   data=p.read_bytes();w.writerow([p.relative_to(R).as_posix(),len(data),sha(data)])
 archive=R.parent/'Codex_Verification_v2_800_2026-11-07.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in files+[manifest]:z.write(p,'codex_verification_v2/'+p.relative_to(R).as_posix())
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  for row in csv.DictReader(manifest.open()):
   b=z.read('codex_verification_v2/'+row['path']);assert len(b)==int(row['bytes']) and sha(b)==row['sha256'],row['path']
 result={'created_utc':datetime.now(timezone.utc).isoformat(),'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive.read_bytes()),'payload_files':len(files),'archive_entries':len(files)+1,'crc_and_payload_hashes':'passed','github_policy':'Unpacked files only; no duplicate zip blob.'}
 (R/'ZIP_PACKAGING.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
