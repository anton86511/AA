# AA — iSponsorBlock → YouTube IPA

把 `tweak/iSponsorBlock.dylib`（及 `iSponsorBlock.bundle`）注入「已解密的官方 YouTube IPA」。

## 用法
1. 把解密後的 YouTube `.ipa` 放到可直接下載的連結（例如自己 repo 的 Release 附件）。
2. GitHub → Actions → **Inject iSponsorBlock into IPA** → Run workflow，貼上 IPA 連結。
3. 完成後在 Artifacts 下載 `YouTube-iSponsorBlock.ipa`，再用 Sideloadly / AltStore / TrollStore 等簽名安裝。

本機也可執行：`pip install lief && python3 scripts/inject.py YouTube.ipa out.ipa [--substrate libellekit.dylib]`

## 注意
- 輸出 IPA 未簽名（簽章已移除），必須自行重新簽名。
- 預設會移除 `PlugIns`/`Extensions`/`Watch`（App Extension），避免旁載時出現 "Failed to set app extension placeholders" 的 bundle ID 不符錯誤；要保留請加 `--keep-extensions`。
- 來源 IPA 若仍加密（cryptid≠0）腳本會直接報錯。
- tweak 來源：Galactic-Dev/iSponsorBlock（GPL）。

## 去廣告版本：uYouEnhanced
Actions → **Build uYouEnhanced (ad-blocking build)**：從 `anton86511/uYouEnhanced`（含 uYou + iSponsorBlock 等）編譯，貼上解密 YouTube IPA 連結即可，成品在本 repo 的 Releases（draft）。
