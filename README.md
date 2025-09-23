# 🍎 FoodLoop - Food Donation Platform

![Django](https://img.shields.io/badge/Django-5.2.5-green)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.1.3-purple)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)

**Connecting Communities to Combat Food Waste Through Sharing**

FoodLoop is a comprehensive web platform that bridges the gap between food donors and recipients, enabling communities to reduce food waste while helping those in need. Our mission is to create sustainable food sharing ecosystems across neighborhoods.

## 🌟 Key Features

### 🎯 Core Functionality

- **Dual-Role System**: Register as Donor or Recipient with specialized dashboards
- **Smart Donation Management**: Create, browse, claim, and track food donations
- **Geolocation Services**: Interactive maps with location-based donation discovery
- **Mutual Rating System**: Build trust through reciprocal donor-recipient ratings
- **Real-time Notifications**: Instant alerts for new donations and claims

### 🛡️ Security & Trust

- **Email Verification**: Secure account verification system
- **Role-based Access**: Protected routes for donors and recipients
- **Rating & Reputation**: Community-driven trust building
- **Secure File Uploads**: Protected image handling with validation

### 📱 User Experience

- **Responsive Design**: Mobile-first approach works on all devices
- **Intuitive Interface**: Clean, modern UI with Bootstrap 5
- **Advanced Search**: Filter donations by type, location, and distance
- **Progress Tracking**: Visual donation status indicators

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Django 5.2.5
- SQLite (default) or PostgreSQL

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/foodloop.git
cd foodloop
```

2. **Create virtual environment**

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Run migrations**

```bash
python manage.py makemigrations
python manage.py migrate
```

5. **Create superuser** (optional)

```bash
python manage.py createsuperuser
```

6. **Run development server**

```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000` to see your application running!

## 📁 Project Structure

```
FoodLoop/
├── core/                          # Main application
│   ├── models.py                  # Database models (User, Donation, Rating)
│   ├── views.py                   # View functions and business logic
│   ├── forms.py                   # Django forms for data validation
│   ├── urls.py                    # URL routing configuration
│   ├── templates/                 # HTML templates
│   │   ├── base.html             # Base template structure
│   │   ├── donor/                # Donor-specific templates
│   │   ├── recipient/            # Recipient-specific templates
│   │   └── ratings/              # Rating system templates
│   └── static/                   # CSS, JavaScript, images
├── foodloop/                     # Project configuration
│   ├── settings.py               # Django settings
│   └── urls.py                   # Project URL configuration
└── manage.py                     # Django management script
```

## 🗃️ Database Models

### Core Entities

- **UserProfile**: Extended user model with role-specific data
- **Donation**: Food donation listings with status tracking
- **Rating**: Mutual rating system between donors and recipients
- **EmailVerification**: Secure email confirmation system

### Status Workflow

```
Donation Creation → Available → Claimed → Completed → Rated
```

## 🎨 UI Components

### Dashboard Features

- **Donor Dashboard**: Donation management, statistics, rating prompts
- **Recipient Dashboard**: Available donations, claim history, contact management
- **Interactive Maps**: Leaflet.js integration for geographical discovery
- **Rating Interface**: 5-star system with optional comments

### Responsive Design

- Mobile-optimized navigation
- Touch-friendly interfaces
- Progressive enhancement approach

## 🔧 Configuration

### Environment Setup

Update `foodloop/settings.py` for production:

```python
# Email Configuration (Production)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'your-smtp-server.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

# Database (Production)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'foodloop_db',
        'USER': 'your_username',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Key Settings

- **DEBUG**: Set to `False` in production
- **ALLOWED_HOSTS**: Configure for your domain
- **STATIC_ROOT**: Set for production static files
- **MEDIA_ROOT**: Configure for file uploads

## 🚀 Deployment

### Using PythonAnywhere

1. Upload project files
2. Create virtual environment
3. Install requirements
4. Configure WSGI file
5. Set up static files

### Using Heroku

```bash
# Create Procfile
web: python manage.py runserver 0.0.0.0:$PORT --noreload

# Deploy
git push heroku main
heroku run python manage.py migrate
```

## 🔒 Security Features

- **CSRF Protection**: All forms include CSRF tokens
- **XSS Prevention**: Template auto-escaping enabled
- **SQL Injection Protection**: ORM usage prevents injections
- **File Upload Validation**: Type and size restrictions
- **Password Hashing**: Django's built-in secure hashing

## 📊 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Home page with available donations |
| GET | `/map/` | Interactive donations map |
| POST | `/donation/create/` | Create new donation |
| POST | `/donation/{id}/claim/` | Claim a donation |
| POST | `/donation/{id}/rate/` | Rate a completed donation |
| GET | `/search/` | Advanced donation search |

## 🧪 Testing

Run the test suite:

```bash
python manage.py test core
```

Test coverage includes:

- User authentication and authorization
- Donation creation and claiming
- Rating system functionality
- Form validation and error handling

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📈 Performance Optimizations

- **Database Indexing**: Optimized queries for large datasets
- **Static File Compression**: Minified CSS and JavaScript
- **Image Optimization**: Automatic resizing and compression
- **Template Caching**: Efficient rendering performance
- **Lazy Loading**: Optimized image loading

## 🌍 Environmental Impact

FoodLoop contributes to UN Sustainable Development Goals:

- **SDG 2**: Zero Hunger
- **SDG 12**: Responsible Consumption and Production
- **SDG 13**: Climate Action

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/fredxotic/foodloop/issues)
- **Email**: charlesfred285@gmail.com

## 🙏 Acknowledgments

- Django community for excellent documentation
- Bootstrap team for responsive UI components
- Leaflet.js for mapping functionality
- Font Awesome for beautiful icons
- All our contributors and beta testers

---

## 🔄 Changelog

### v1.0.0 (Current)

- Initial production release
- Complete donor/recipient workflow
- Rating system implementation
- Map integration
- Email verification system

### v0.9.0

- Beta testing phase
- UI/UX improvements
- Performance optimizations
- Security enhancements

---
