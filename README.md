# 🌾 Agricultural AI Advisor

**Empowering Indian farmers with AI-powered insights and tools.**

![Version](https://img.shields.io/badge/version-2.0-blue)
![Python](https://img.shields.io/badge/Python-3.9+-brightgreen)
![Framework](https://img.shields.io/badge/Framework-Streamlit-red)
![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

<!-- Placeholder for a GIF or screenshot of the application in action -->
![App Demo](https://via.placeholder.com/800x400.png?text=App+Demo+Screenshot)

---

## 📖 Overview

The **Agricultural AI Advisor** is a comprehensive, multi-agent system designed to support Indian farmers by providing real-time, data-driven advice. From detecting crop diseases to offering financial guidance and navigating government policies, this tool leverages advanced AI to enhance decision-making and improve agricultural outcomes.

## ✨ Key Features

| Feature                 | Description                                                                                                     |
| ----------------------- | --------------------------------------------------------------------------------------------------------------- |
| **🌱 Disease Detection**    | Upload plant images for instant AI diagnosis and receive tailored treatment recommendations.                    |
| **🌤️ Weather Insights**     | Access real-time weather data and forecasts to make informed decisions about farming activities.                |
| **💰 Financial Advisor**    | Get detailed financial planning, including ROI analysis, investment guidance, and crop profitability metrics.   |
| **🏛️ Government Schemes**   | Discover relevant government policies, subsidies, and schemes based on your profile and location.               |
| **🤖 Multilingual Chat**   | Interact with a context-aware AI assistant in multiple Indian languages via text or voice.                      |
| **🔒 Secure & Persistent** | Your data is safe with robust user authentication and a local SQLite database for persistence.                  |
| **🐳 Dockerized**          | The entire application is containerized, allowing for a consistent and easy setup using Docker Compose.         |

## 🛠️ Tech Stack

- **Backend**: Python
- **Framework**: Streamlit
- **AI/ML**: Groq (Llama 3.1, Whisper), EasyOCR, Pytesseract
- **Database**: SQLite
- **Containerization**: Docker, Docker Compose
- **Scheduling**: `schedule`
- **Web Scraping**: `trafilatura`

## 🚀 Getting Started

### Prerequisites

- [Python 3.9+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/)
- [Docker](https://www.docker.com/products/docker-desktop/) (for containerized setup)

### 1. Clone the Repository

```bash
git clone https://github.com/Sak245/agri.git
cd agri
```

### 2. Set Up Environment Variables

Create a file named `.env` in the project root by copying the example file:

```bash
# For Windows
copy .env.example .env

# For macOS/Linux
cp .env.example .env
```

Now, open the `.env` file and add your API keys. At a minimum, the `GROQ_API_KEY` is required.

```env
# Required for core AI features
GROQ_API_KEY="your_groq_api_key_here"

# Required for weather data
OPENWEATHER_API_KEY="your_openweather_api_key_here"

# Optional for WhatsApp notifications
TWILIO_ACCOUNT_SID="your_twilio_account_sid"
TWILIO_AUTH_TOKEN="your_twilio_auth_token"
TWILIO_WHATSAPP_NUMBER="whatsapp:+14155238886"
```

### 3. Run with Docker Compose (Recommended)

This is the easiest way to get started. Ensure Docker Desktop is running on your system.

```bash
docker-compose up --build
```

The application will be available at `http://localhost:8501`.

### 4. Manual Installation (without Docker)

If you prefer not to use Docker, you can run the application locally:

```bash
# Create and activate a virtual environment
python -m venv venv
# Windows: .\venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the Streamlit app
streamlit run app.py
```

## 📁 Project Structure

```
agri/
├── agents/              # Core AI agent logic
│   ├── agricultural_agents.py
│   └── ...
├── services/            # Background services (e.g., OCR)
│   ├── ocr_server.py
│   └── ...
├── utils/               # Shared utilities and managers
│   ├── database_manager.py
│   ├── auth_manager.py
│   └── ...
├── .env.example         # Example for environment variables
├── app.py               # Main Streamlit application entrypoint
├── compose.yml          # Docker Compose setup for all services
├── dockerfile.prod      # Dockerfile for the main application
└── requirements.txt     # Python dependencies
```

## 🤝 Contributing

Contributions are welcome! If you'd like to help improve the project, please follow these steps:

1.  **Fork** the repository.
2.  Create a new **branch** (`git checkout -b feature/your-feature`).
3.  **Commit** your changes (`git commit -m 'Add some feature'`).
4.  **Push** to the branch (`git push origin feature/your-feature`).
5.  Open a **Pull Request**.

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for more details.

## 🙏 Acknowledgments

- The **Streamlit** team for their amazing web framework.
- **Groq** for providing powerful and fast AI models.
- The open-source community for the libraries and tools that made this project possible.