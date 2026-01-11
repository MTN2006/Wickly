# Wickly 📈🕯️ (Single-Developer Project)

**AI-Powered Candlestick Pattern Recognition & Real-Time Stream Analysis**

**Live Demo:** [Click](https://wickly-production.up.railway.app/flask/)

### Developer
* **Muhammad Talha** (Computing Science, University of Alberta)

---

## Inspiration 💡
Technical analysis is a cornerstone of trading, yet manually identifying patterns across hundreds of charts is time-consuming and prone to human error. Traders often miss critical entry points because they cannot monitor dozens of patterns across multiple timeframes simultaneously. I wanted to explore whether computer vision could be used to measure market sentiment and turn visual candle data into actionable, real-time signals.

That idea became **Wickly**: a project that transforms static financial charts and live data streams into meaningful feedback to help traders understand market movements.

## What It Does 🤔
Wickly is a high-performance web application that uses a custom-trained Convolutional Neural Network (CNN) to analyze market data and identify over 30 unique candlestick patterns with high precision.

**The system:**
* **Streams Live Market Data:** Monitors live data feeds to identify patterns as they form in real-time.
* **Accepts Image Uploads:** Allows users to upload chart snippets for instant classification.
* **Identifies 30+ Patterns:** Recognizes complex formations such as "Morning Star," "Hammer," and "Engulfing" patterns.
* **Delivers Sub-Second Inference:** Optimized REST APIs ensure analysis happens with minimal latency for live trading.
* **Automated Feature Extraction:** Automatically detects trend reversals and continuation signals without manual input.

## How It Works ⚙️

### 1. Data Engineering & CNN Training
I engineered and trained a custom CNN using **Fastai** on a large-scale dataset of 10,000+ candlestick images. This required labeling and balancing 30+ unique pattern classes. I applied data augmentation techniques to ensure the model remains robust against different chart scales, colors, and resolutions.

### 2. High-Performance API Architecture
The backend uses a hybrid architecture of **FastAPI** and **Flask**. FastAPI handles the high-concurrency requirements of the live pattern streaming, while Flask manages the core web routing. This dual-framework approach ensures that heavy model inference does not block the user interface.



### 3. Real-Time Processing Engine
Unlike standard image classifiers, Wickly includes a dedicated processing layer for live streams. It captures frames from market data feeds, normalizes them into tensors, and runs them through the neural network in a continuous loop, providing "live" detection markers as the market moves.

### 4. Production Pipeline & DevOps
The entire stack is containerized using **Docker** and deployed on a professional CI/CD pipeline. This ensures that the environment is identical from development to production, preventing "it works on my machine" errors during the heavy model loading phase.

## Tech Stack 🛠️
* **Languages:** Python, JavaScript, HTML/CSS, SQLite
* **ML Frameworks:** Fastai, NumPy, Pandas, PyTorch
* **Backend:** FastAPI, Flask
* **Frontend:** Tailwind CSS, JavaScript
* **Deployment:** Railway, Render, Docker

## Getting Started 🚀

### Prerequisites
* Python 3.9+
* FastAPI / Flask
* Fastai & PyTorch

### Installation
```bash
pip install fastapi flask fastai numpy pandas torch
