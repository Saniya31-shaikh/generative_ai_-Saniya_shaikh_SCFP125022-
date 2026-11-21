# Lab 7 — Agentic RAG on Union Budget 2026–27

## Project Overview

This project implements an **Agentic Retrieval-Augmented Generation (RAG)** system using India's Union Budget 2026–27 Speech as the knowledge source.

The system allows users to ask questions about budget policies, government schemes, fiscal allocations, and financial figures. It retrieves relevant information from the Budget document and generates answers using an LLM.

Unlike a basic RAG pipeline, this implementation also includes tool calling, allowing the model to decide when to search the document, perform calculations, or respond directly.

## Objectives

- Extract and process information from the Union Budget PDF.
- Convert document text into embeddings for semantic search.
- Store and retrieve relevant chunks using ChromaDB.
- Create a LangChain tool for searching the Budget document.
- Integrate Groq LLM for question answering.
- Add a calculator tool for arithmetic operations.
- Evaluate tool selection using different types of queries.

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Main programming language |
| Google Colab | Development environment |
| LangChain | LLM integration and tool calling |
| Docling | PDF ingestion and document processing |
| Hugging Face | Sentence embedding generation |
| ChromaDB | Vector database for semantic search |
| Groq | LLM inference |
| OpenAI GPT-OSS 20B | Language model accessed through Groq |
| Pandas | Evaluation results |

## Dataset

**Document:** Union Budget 2026–27 Speech  
**Presented by:** Nirmala Sitharaman, Minister of Finance  
**Date:** 1 February 2026  
**Source file:** `budget_speech.pdf`

The document contains proposals related to economic growth, infrastructure, healthcare, taxation, manufacturing, agriculture, and government expenditure.

## Implementation

### 1. Document Ingestion and Preprocessing

First, I loaded the Budget Speech PDF using `DoclingLoader` and extracted the document text and metadata.

I cleaned the extracted content, preserved page-number information, and divided the document into smaller chunks using `RecursiveCharacterTextSplitter`.

**Chunk configuration:**
- Chunk size: 1000 characters
- Chunk overlap: 200 characters
- Extracted document segments: 171
- Generated text chunks: 212

### 2. Embeddings and Vector Database

I used the Hugging Face `sentence-transformers/all-mpnet-base-v2` embedding model to convert the text chunks into vector representations.

These embeddings were stored in **ChromaDB** to support semantic similarity search.

The retriever searches for relevant Budget passages and returns their content along with page references.

### 3. Budget Search Tool

I created a custom LangChain tool named `search_budget` using the `@tool` decorator.

This tool searches ChromaDB for the three most relevant document chunks and provides the retrieved text with page-number information.

### 4. Groq LLM Integration

I integrated the `openai/gpt-oss-20b` model through Groq using `ChatGroq`.

The model receives instructions to use the retrieved Budget information for factual answers, provide page citations, and avoid unsupported claims.

### 5. Calculator Tool

I implemented a `calculator` tool for basic arithmetic operations using Python's `ast` module.

The agent can use this tool for numerical calculations and combine it with document retrieval when answering Budget-related questions.

For example, the agent retrieved the allocations for Biopharma SHAKTI, Container Manufacturing, and CCUS, then calculated their combined outlay.

### 6. Agentic Tool Calling

The system uses LangChain's tool-binding functionality and a custom agent loop.

Depending on the question, the model can:

- Call `search_budget` for Budget-specific information.
- Call `calculator` for arithmetic.
- Use both tools for questions requiring retrieval and calculations.
- Respond directly to simple conversational questions.

An interactive chat loop is also included, allowing users to ask multiple questions until they enter `exit`.

## Sample Results

| Question | Result |
|---|---|
| What is the outlay of Biopharma SHAKTI? | ₹10,000 crore over five years |
| Compare the fiscal deficit for 2025–26 and 2026–27. | 4.4% and 4.3% of GDP, respectively |
| Calculate the increase in public capital expenditure. | Approximately 8.9% |
| What is the combined outlay of Biopharma SHAKTI, Container Manufacturing, and CCUS? | ₹40,000 crore |
| Hi, how are you? | Answered directly without document search |

The Budget-related answers were generated using retrieved document passages with page references.

## Evaluation

I tested the system with **eight queries** covering factual retrieval, document comparison, general conversation, numerical reasoning, and multi-step tool usage.

The notebook records the tool decisions and final responses in an evaluation table.

**Recorded tool-selection result: 8/8 expected decisions (100%).**

However, one query about income tax slab rates did not produce a successful final answer because the agent reached its maximum number of tool-calling rounds. This demonstrates a limitation in retrieval and agent execution, even when the tool-selection decision is appropriate.

## How to Run

1. Open `Lab7_Agentic_RAG_Union_Budget_ipynb.ipynb` in Google Colab.
2. Upload `budget_speech.pdf` to the Colab runtime.
3. Install the required libraries using the first installation cell.
4. Configure `GROQ_API_KEY` in Colab Secrets and enable notebook access.
5. Run the notebook cells in sequence.
6. Execute the sample queries or use the interactive chat loop.

**Note:** The notebook uses `/content/budget_speech.pdf` as the input path. The PDF must be available at this location before document ingestion.

## Limitations

- Retrieval quality depends on the relevance of the stored document chunks.
- Some queries may require repeated tool calls or may not reach a final answer.
- The model's numerical reasoning and factual responses still require verification against the source document.
- ChromaDB should be initialized with a clean collection when rebuilding the index to avoid duplicate stored chunks.

## Conclusion

This assignment helped me understand how RAG can be combined with tool calling to build a document-based AI assistant. I implemented PDF ingestion, text chunking, embeddings, vector search, Groq integration, and a calculator tool. I also tested how the model chooses between document search, calculations, and direct responses.

The project demonstrates how Agentic RAG can support factual question answering and basic numerical analysis of government Budget documents.

---

**Lab:** 7 — Generative AI  
**Project:** Agentic RAG on Union Budget 2026–27  
**Environment:** Google Colab
