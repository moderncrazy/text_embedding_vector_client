# Text to Embedding README

# 概述 (Overview)

**Text to Embedding** 插件用于在 Dify 工作流中将文本转换为向量表示。  
它支持 **动态配置与灵活选择向量化模型**，并提供 **批量处理限制**，  
有效防止一次性处理过多数据导致的 **显存溢出**。

# 1、Text to Embedding 工具

**Text to Embedding**：通过调用不同的向量化模型，将文本转化为高维向量，  
可用于搜索、推荐、语义检索等场景。  
插件支持在工作流中灵活选择模型，并限制批量处理大小，提升稳定性。

## 1.1、配置方法 (Configuration)

将插件集成到 Dify 的步骤如下：

1. 打开 **Plugin Marketplace（插件市场）**。
2. 搜索 **Text to Embedding**。
3. 点击安装插件并完成集成。

## 1.2、工具特性 (Tool Features)

**Text to Embedding** 插件包含多个可自定义的参数，以满足不同的向量化需求：

### 文本向量化

将输入文本转化为向量表示，支持批量处理。

**输入参数 (Input Variables)：**
- **文本内容 (必填)**：需要向量化的文本，可以是单条或多条。
- **模型名称 (必填)**：向量化模型的名称（例如 `text-embedding-3-large`）。
- **批量大小限制 (可选)**：用于限制单次处理的文本数量，避免显存溢出。

**输出结果 (Output)：**
- 返回对应的向量数组，可直接用于搜索、聚类、相似度计算等场景。

## 1.3、使用方法 (Usage)

**Text to Embedding** 可与 **Chatflow / Workflow Apps** 和 **Agent Apps** 无缝集成。

### Chatflow / Workflow Apps
1. 在 Chatflow 或 Workflow 中添加 **Text to Embedding** 节点。
2. 配置“文本向量化”操作，输入文本并选择模型及批量限制。
3. 运行流程后即可获取文本对应的向量结果，用于下游处理。

### Agent Apps
1. 在 Agent 应用中添加 **Text to Embedding** 工具。
2. 在聊天界面输入需要向量化的文本。
3. 插件将返回对应的向量结果。

## 1.4、应用场景 (Use Cases)

- **语义搜索**：将文本转换为向量后进行语义检索，提高搜索准确度。
- **推荐系统**：利用文本向量相似度进行个性化推荐。
- **知识库构建**：为大规模文档生成嵌入向量，支持高效检索。
- **自然语言处理**：可用于文本聚类、相似度计算、意图识别等多种 NLP 任务。
