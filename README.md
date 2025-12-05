# FoodLoop - Community Food Sharing Platform 🍃

![Status](https://img.shields.io/badge/Status-Beta_MVP-orange)
![Python](https://img.shields.io/badge/Python-3.13-blue)
![Django](https://img.shields.io/badge/Django-5.2-green)

**FoodLoop** is a hyper-local food rescue platform connecting donors (restaurants, individuals) with surplus food to recipients (communities, charities) who need it. 

> **Phase 1 Update:** The platform has been optimized for performance and stability. GPS dependencies have been replaced with simplified location grouping, and a service-oriented architecture has been implemented.

## 🌟 Key Features

### For Donors
- **Inventory Management**: Create donations with images, expiry dates, and categories.
- **Smart Recommendations**: The system suggests what to donate based on current demand and seasonality.
- **Impact Analytics**: Track calories saved and community impact via interactive charts.
- **Reputation System**: Earn ratings and build trust within the community.

### For Recipients
- **Dietary Matching**: Set preferences (Vegan, Halal, etc.) to get filtered recommendations.
- **Claim System**: Reserve food instantly and coordinate pickup times.
- **Nutrition Insights**: Track the nutritional value of claimed food over time.
- **Location Browsing**: Find available donations grouped by neighborhood.

### Technical Highlights
- **Service Layer Architecture**: Business logic decoupled from Views/Models for testability.
- **Advanced Caching**: Custom `CacheManager` with pre-warming strategies for high-performance dashboards.
- **API First**: Full REST API (DRF) with JWT Authentication and Throttling (Rate Limiting).
- **Security**: Email verification, input sanitization, and role-based access control decorators.
- **Responsive UI**: Built with Tailwind CSS and Alpine.js for a seamless mobile experience.

## Tech Stack

- **Backend**: Django 5.2, Django REST Framework
- **Database**: SQLite (Dev) / PostgreSQL (Prod)
- **Frontend**: Django Templates, Tailwind CSS (CDN), Alpine.js, Chart.js
- **Media**: Cloudinary integration for image optimization
- **Async/Tasks**: Celery & Redis configuration ready

## Installation & Setup

### Prerequisites
- Python 3.10+
- Virtualenv

### 1. Clone & Environment
```bash
git clone https://github.com/fredxotic/foodloop.git
cd foodloop
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
````

### 2\. Dependencies

```bash
pip install -r requirements.txt
```

### 3\. Configuration

Create a `.env` file in the root directory:

```env
DEBUG=True
SECRET_KEY=your-secret-key
# Optional: Add Cloudinary/Email credentials here
```

### 4\. Database & Seeding

We have a custom command to set up the database and populate it with demo data:

```bash
python manage.py migrate
python manage.py setup_foodloop --create-superuser --create-sample-data --setup-directories
```

*This creates a superuser (admin/admin123) and sample donors/recipients.*

### 5\. Run Server

```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000`

## 📚 API Documentation

The API is available at `/api/v1/`.

  * **Auth**: `/api/v1/token/` (Obtain JWT)
  * **Donations**: `/api/v1/donations/`
  * **Users**: `/api/v1/users/`

## 🗺️ Roadmap

### Phase 1 (Completed) ✅

  - [x] Core Authentication & Role Management
  - [x] Donation CRUD & Claim Workflow
  - [x] Notification System (Polling based)
  - [x] Service-Oriented Refactor
  - [x] Basic Analytics Dashboard

### Phase 2 (In Progress) 🚧

  - [ ] Integration of Mapbox/Google Maps for precise geolocation
  - [ ] Real-time WebSocket notifications (Django Channels)
  - [ ] PWA (Progressive Web App) capabilities for offline support
  - [ ] Stripe/M-Pesa integration for monetary support to NGOs

-----

*Built with ❤️ by fredxotic*