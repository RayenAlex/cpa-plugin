# CPA 插件仓库

[CLIProxyAPI (CPA)](https://github.com/router-for-me/CLIProxyAPI) 插件集合。当前提供独立发布的 **Quota Center** 与 **额度预热** 插件。

## 插件

| ID | 说明 | 源码 |
|---|---|---|
| `quota-center` | 多供应商额度中心：智谱、MiniMax、方舟、Codex、Gemini 和 Grok。支持 CPA 原生认证复用、手动账号和额度看板。 | [独立插件仓库](https://github.com/RayenAlex/quota-center) |
| `cpa-quota-warmup` | 按计划用极短请求预热 CPA 认证账号的 5 小时额度窗口。 | [szxypi/cpa-quota-warmup](https://github.com/szxypi/cpa-quota-warmup) |
| `cpa-devin-prompt-compat` | 为 Devin 模型请求替换会触发上游 403 content policy 的固定系统提示词措辞。 | [szxypi/cpa-devin-prompt-compat](https://github.com/szxypi/cpa-devin-prompt-compat) |

## 插件工件

插件工件遵循 CLIProxyAPI 插件商店的标准命名：

~~~text
<id>_<version>_<goos>_<goarch>.zip
~~~

ZIP 根目录只包含平台动态库：

~~~text
quota-center_0.2.1_linux_amd64.zip    # quota-center.so
quota-center_0.2.1_darwin_arm64.zip                   # quota-center.dylib
cpa-quota-warmup_<version>_linux_amd64.zip            # cpa-quota-warmup.so
cpa-quota-warmup_<version>_linux_arm64.zip            # cpa-quota-warmup.so
cpa-devin-prompt-compat_0.1.1_linux_amd64.zip        # cpa-devin-prompt-compat.so
cpa-devin-prompt-compat_0.1.1_linux_arm64.zip        # cpa-devin-prompt-compat.so
~~~

`quota-center` 的源码、构建和 Release 工作流位于 [RayenAlex/quota-center](https://github.com/RayenAlex/quota-center)。`cpa-quota-warmup` 使用上游 GitHub Release 发布的 Linux amd64 与 Linux arm64 工件。`cpa-devin-prompt-compat` 同样使用上游 Release 发布的 Linux amd64 与 Linux arm64 工件。

本仓库只维护商店 registry、可安装工件和校验工具。

## 安装

### 通过插件商店安装

在 CLIProxyAPI 配置中添加自定义商店源：

~~~yaml
plugins:
  enabled: true
  store-sources:
    - "https://raw.githubusercontent.com/RayenAlex/cpa-plugin/main/registry.json"
~~~

刷新插件商店后，安装或更新 `quota-center`、`cpa-quota-warmup` 或 `cpa-devin-prompt-compat`。

### 直接下载工件

`quota-center` 以 Linux amd64 为例：

~~~bash
curl -L -o quota-center_0.2.1_linux_amd64.zip \
  https://github.com/RayenAlex/quota-center/releases/download/v0.2.1/quota-center_0.2.1_linux_amd64.zip
unzip quota-center_0.2.1_linux_amd64.zip
~~~

将解压出的 `quota-center.so` 放入 CPA 的插件目录，并在配置中启用：

~~~yaml
plugins:
  enabled: true
  dir: "plugins"
  configs:
    quota-center:
      enabled: true
~~~

插件商店安装会自动按 `GOOS/GOARCH` 选择工件并校验 SHA-256。

`cpa-quota-warmup` 当前提供 Linux amd64 与 Linux arm64 工件。请优先从插件商店安装；它会自动选择对应平台、下载上游 Release ZIP 并验证 SHA-256。完整配置项与工作机制请见 [上游 README](https://github.com/szxypi/cpa-quota-warmup#readme)。

`cpa-devin-prompt-compat` 当前也提供 Linux amd64 与 Linux arm64 工件。安装后在 `plugins.configs.cpa-devin-prompt-compat` 中启用；默认仅匹配 `devin/*` 模型。其替换规则与配置示例请见 [上游 README](https://github.com/szxypi/cpa-devin-prompt-compat#readme)。

## 远程更新

在 CPA 插件商店中添加：

~~~text
https://raw.githubusercontent.com/RayenAlex/cpa-plugin/main/registry.json
~~~

然后在商店 UI 中安装或更新 `quota-center`、`cpa-quota-warmup` 或 `cpa-devin-prompt-compat`。

## Registry 与验证

正式 registry 位于 [registry.json](registry.json)。`quota-center` 与 `cpa-devin-prompt-compat` 引用各自上游的 GitHub Release；`cpa-quota-warmup` 由同步工作流引用其最新稳定上游 Release 的 Linux 工件与 SHA-256。

本地验证：

~~~bash
python3 scripts/validate-registry.py registry.json
python3 scripts/check-registry-artifacts.py registry.json \
  --artifacts-dir artifacts \
  --url-prefix https://raw.githubusercontent.com/RayenAlex/cpa-plugin/main/artifacts
python3 -m unittest discover -s tests -p 'test_*.py' -v
~~~

`check-registry-artifacts.py` 会检查 Release URL 的平台、版本、文件名及 SHA-256 格式。

## 自动同步 `cpa-quota-warmup`

[同步工作流](.github/workflows/sync-cpa-quota-warmup.yml) 每 6 小时运行一次，也可从 GitHub Actions 手动触发。它读取上游最新稳定 Release，要求 Linux amd64 与 Linux arm64 ZIP 均已发布，然后用其版本与 SHA-256 更新 `registry.json`、运行验证并自动提交。
