# Text to Embedding README

# Overview

The **Text to Embedding** plugin is used to convert text into vector representations within Dify workflows.  
It supports **dynamic configuration and flexible selection of vectorization models**, and provides **batch processing limits**,  
effectively preventing **GPU memory overflow** caused by processing excessive data at once.

# 1. Text to Embedding Tool

**Text to Embedding**: Converts text into high-dimensional vectors by calling different vectorization models.  
It can be used for scenarios such as search, recommendation, and semantic retrieval.  
The plugin supports flexible model selection within workflows and limits batch processing size to enhance stability.

## 1.1 Configuration

Follow these steps to integrate the plugin into Dify:

1. Open the **Plugin Marketplace**.
2. Search for **Text to Embedding**.
3. Click to install the plugin and complete the integration.

## 1.2 Tool Features

The **Text to Embedding** plugin includes several customizable parameters to meet various vectorization needs:

### Text Vectorization

Converts input text into vector representations and supports batch processing.

**Input Variables:**
- **Text Content (Required)**: The text to be vectorized. It can be a single string or multiple strings.
- **Model Name (Required)**: The name of the vectorization model (e.g., `text-embedding-3-large`).
- **Batch Size Limit (Optional)**: Used to limit the number of texts processed in a single batch to avoid GPU memory overflow.

**Output:**
- Returns the corresponding vector array, which can be directly used for search, clustering, similarity calculation, and other scenarios.

## 1.3 Usage

**Text to Embedding** can be seamlessly integrated with **Chatflow / Workflow Apps** and **Agent Apps**.

### Chatflow / Workflow Apps
1. Add a **Text to Embedding** node to your Chatflow or Workflow.
2. Configure the "Text Vectorization" operation: input the text, select the model, and set the batch limit.
3. After running the workflow, obtain the vector results corresponding to the text for downstream processing.

### Agent Apps
1. Add the **Text to Embedding** tool to your Agent application.
2. Enter the text you want to vectorize in the chat interface.
3. The plugin will return the corresponding vector results.

## 1.4 Use Cases

- **Semantic Search**: Convert text into vectors for semantic retrieval, improving search accuracy.
- **Recommendation Systems**: Utilize text vector similarity for personalized recommendations.
- **Knowledge Base Construction**: Generate embedding vectors for large-scale documents to support efficient retrieval.
- **Natural Language Processing (NLP)**: Can be used for various NLP tasks such as text clustering, similarity calculation, and intent recognition.