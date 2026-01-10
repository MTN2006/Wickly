Wickly 📈🕯️ (Single-Developer Project)
AI-Powered Candlestick Pattern Recognition & Real-Time Stream Analysis

Live Demo: [Wickly](https://wickly-production.up.railway.app/flask/)


Developer: Muhammad Talha 

Inspiration 💡
Technical analysis is a cornerstone of trading, yet manually identifying patterns across hundreds of charts is time-consuming and prone to human error. I wanted to see if I could automate the "eyes" of a trader using computer vision. Wickly was built to transform static financial charts into actionable, real-time insights by detecting over 30 unique candlestick patterns instantly.

What It Does 🤔
Wickly is a high-performance web application that uses a custom-trained Convolutional Neural Network (CNN) to analyze trading charts. The system:


Accepts Image Uploads: Users can upload snippets of financial charts for immediate classification.


Identifies 30+ Patterns: Recognizes complex formations like "Morning Star," "Hammer," and "Engulfing" patterns.

Real-Time Live Stream: Monitors live market data streams to identify patterns as they form on the chart.


Delivers Sub-Second Inference: Optimized REST APIs ensure the analysis happens with minimal latency.


Logs Analytics: Tracks detections and allows for future backtesting and alerts.

Real-Time Pattern Streaming 🌊
Unlike static analysis tools, Wickly features a Live Stream Integration engine:

Live Ingestion: Processes live market data feeds to provide continuous pattern monitoring.

Instant Detection: The system flags emerging patterns in real-time, allowing for immediate feedback.

Dynamic Visualization: A real-time patterns section on the dashboard updates as the CNN processes new frames from the stream.

How It Works ⚙️

Model Training: I engineered and trained a custom CNN using Fastai on a large-scale dataset of 10,000+ candlestick images to ensure high classification accuracy across 30+ classes.


API Layer: Developed using a hybrid of Flask and FastAPI to provide high-performance endpoints for image inference and stream management.


Database Management: Utilized SQLite to architect modular structures for storing detections, user alerts, and historical analytics.


Frontend Interface: Built a polished, responsive frontend with Tailwind CSS featuring a dynamic pattern library and an intuitive upload/streaming portal.


Deployment: Containerized the entire stack and deployed it to Railway/Render, ensuring a production-ready environment.

Tech Stack 🛠️

Languages: Python, JavaScript, HTML/CSS, SQLite 


ML Frameworks: Fastai, NumPy, Pandas 


Backend: FastAPI, Flask 


Frontend: Tailwind CSS, JavaScript 


Deployment: Railway, Render, Docker 

Getting Started 🚀
Prerequisites
Python 3.9+

FastAPI / Flask

Fastai & PyTorch

Installation
Bash

pip install fastapi flask fastai numpy pandas
Running the Project
Start the Backend:

Bash

python main.py
Access the Platform: Navigate to https://wickly-production.up.railway.app/flask/ or your local server address (e.g., localhost:8000) to access the upload and live streaming portal.

Challenges I Faced 🧠

Real-Time Latency: Optimizing the model and API to achieve sub-second inference—critical for the fast-paced nature of live market streaming.


Data Scale: Managing and labeling a dataset of 10,000+ images while maintaining balance across 30 different pattern classes.

Stream Handling: Implementing live stream integration to ensure the CNN could handle continuous data without memory leaks or lag.

Accomplishments I’m Proud Of 🏆
Successfully classifying 30+ unique patterns with high precision.

Building a complete end-to-end pipeline from raw data to a live, deployed cloud application.

Implementing a functional live stream integration as a solo developer.

What’s Next 🛤️
Predictive Analytics: Moving beyond pattern recognition to predicting short-term price movements based on volume data.

Multi-Exchange Support: Integrating WebSockets for multiple crypto and stock exchanges simultaneously.

Mobile App: Creating a mobile-first version for traders to receive push notifications for detected patterns.


Built with passion for Finance and AI by Talha Muhammad 📈⚡
