# AA — iSponsorBlock → YouTube IPA

把 `tweak/iSponsorBlock.dylib`（及 `iSponsorBlock.bundle`）注入「已解密的官方 YouTube IPA」。

## 用法
1. 把解密後的 YouTube `.ipa` 放到可直接下載的連結（例如自己 repo 的 Release 附件）。
2. GitHub → Actions → **Inject iSponsorBlock into IPA** → Run workflow，貼上 IPA 連結。
3. 完成後在 Artifacts 下載 `YouTube-iSponsorBlock.ipa`，再用 Sideloadly / AltStore / TrollStore 等簽名安裝。

本機也可執行：`pip install lief && python3 scripts/inject.py YouTube.ipa out.ipa [--substrate libellekit.dylib]`

## 注意
- 輸出 IPA 未簽名（簽章已移除），必須自行重新簽名。
- 來源 IPA 若仍加密（cryptid≠0）腳本會直接報錯。
- tweak 來源：Galactic-Dev/iSponsorBlock（GPL）。
