# 🤖 AI Customer Support Agent

## 📌 Overview

This project implements an autonomous customer support agent that processes customer tickets using LLM reasoning and tool-based execution.

## ⚙️ Tech Stack

* Python
* LangGraph
* LangChain
* Gemini API

## 🚀 How to Run

### 1. Install dependencies

pip install -r requirements.txt

### 2. Run the project

python customerSupport.py

## 🐳 Docker Run

docker build -t support-agent .
docker run -e GOOGLE_API_KEY=your_key support-agent

## 🧠 Features

* Multi-step reasoning agent
* Tool-based execution
* Handles refund, order status, product issues
* Batch ticket processing

## 📊 Output

* audit_log.json
* Tool execution trace
* Final response per ticket
