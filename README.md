# Wickly 📈🕯️ (Single-Developer Project)

**Hybrid AI & Algorithmic Candlestick Pattern Recognition**

**Live Demo:** [Wickly](https://wickly-production.up.railway.app/flask/)

### Developer
* **Muhammad Talha** (Computing Science, University of Alberta)

---

## Inspiration 💡
Technical analysis is a cornerstone of trading, yet manually identifying patterns across hundreds of charts is time-consuming and prone to human error. I wanted to build a tool that solves this by combining the "visual intelligence" of AI with the "mathematical precision" of technical indicators. 

**Wickly** was created to bridge this gap, using a custom CNN for image-based pattern recognition and the industry-standard TA-Lib for live ticker analysis.

## What It Does 🤔
Wickly is a high-performance web application that provides two distinct ways to analyze market data:
* **AI Image Classification:** Users can upload chart snippets, which are processed by a custom-trained Convolutional Neural Network (CNN) to identify 30+ complex patterns.
* **Real-Time Algorithmic Detection:** Uses the **TA-Lib** (Technical Analysis Library) to scan live ticker data and identify patterns (like Dojis, Hammers, and Engulfing lines) instantly as they form.
* **Sub-Second Inference:** Optimized backends ensure that both the AI model and the algorithmic library return results with minimal latency.
* **Live Patterns Dashboard:** A dedicated section that tracks and displays real-time market signals.

## How It Works ⚙️

### 1. The AI Engine (Computer Vision)
I engineered and trained a custom CNN using **Fastai** on a large-scale dataset of 10,000+ candlestick images. This model is specifically used for the "Image Upload" feature, allowing users to get instant AI classification on saved chart screenshots.

### 2. The Real-Time Engine (TA-Lib)
For live market tickers, I implemented **TA-Lib**. This allows the system to perform high-speed mathematical analysis on live price data. By using a programmatic library for live streams instead of a visual model, the system achieves extreme reliability and speed.

### 3. API & Backend
The system runs on a hybrid of **FastAPI** and **Flask**. FastAPI handles the high-performance data requests required for the live patterns section, while Flask manages the core web interface and user interactions.

### 4. Data Layer
Utilized **SQLite** to architect modular structures for logging detections and managing user alerts, ensuring historical data is accessible for review.

## Tech Stack 🛠️
* **Languages:** Python, JavaScript, HTML/CSS, SQLite
* **Core Libraries:** TA-Lib (Technical Analysis Library), Fastai, PyTorch
* **Data Processing:** NumPy, Pandas
* **Backend Frameworks:** FastAPI, Flask
* **Frontend:** Tailwind CSS, JavaScript
* **Deployment:** Railway, Render

