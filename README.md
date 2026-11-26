# IT Helpdesk Management System (Django)

A full-stack web application built using **Python and Django** to streamline internal IT support operations. Employees can raise technical support tickets, attach screenshots or documents, track ticket progress, and communicate with support agents. IT support staff can manage tickets, use AI-assisted tools, and monitor service performance through an analytics dashboard.

---

## 🚀 Key Features

### 👨‍💻 Employee Features
- **User Authentication:** Register, log in, log out, and manage account details.
- **Profile Management:** Update personal profile information and change passwords.
- **Raise Support Tickets:** Submit IT issues with descriptions, categories, priorities, and file attachments.
- **Ticket Tracking:** Monitor ticket status and progress.
- **Ticket Replies:** Communicate with support staff through ticket conversations.
- **Notifications:** Receive updates about ticket replies and status changes.

### 🛠️ IT Support Staff & Admin Features
- **Role-Based Dashboards:** Separate dashboards for employees and support staff.
- **Ticket Management:** View, filter, prioritize, assign, and resolve support tickets.
- **AI-Assisted Services:** AI helper functionality for ticket analysis, categorization, and response suggestions.
- **Analytics & Reports:** View ticket statistics, resolution performance, and category-wise reports.
- **Django Admin Panel:** Manage application data through Django's built-in administration interface.
- **Sample Data Generator:** Populate the application with sample users, categories, and tickets using a custom management command.

---

## 💻 Technology Stack

| Category | Technologies |
|---|---|
| Programming Language | Python |
| Backend Framework | Django |
| Frontend | HTML5, CSS3, Django Templates |
| Database | SQLite3 |
| Styling | Custom CSS |
| Architecture | Django MVT |
| Development Tools | VS Code, Git, GitHub |

---

## 📁 Project Structure

```text
it-helpdesk-management-using-django/
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── helpdesk/
│   ├── management/
│   │   └── commands/
│   │       └── create_test_data.py
│   ├── migrations/
│   ├── admin.py
│   ├── ai_services.py
│   ├── context_processors.py
│   ├── decorators.py
│   ├── forms.py
│   ├── models.py
│   ├── signals.py
│   ├── urls.py
│   └── views.py
│
├── static/
│   └── css/
│       └── custom.css
│
├── templates/
│   ├── base.html
│   ├── 404.html
│   ├── 500.html
│   ├── helpdesk/
│   └── registration/
│
├── manage.py
└── requirements.txt
```

---

## ⚙️ Installation and Setup

Follow these steps to run the project locally.

### 1. Clone the Repository

```bash
git clone https://github.com/meenal-04/it-helpdesk-management-using-django.git

cd it-helpdesk-management-using-django
```

### 2. Create a Virtual Environment

**Windows:**

```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

If the project uses API keys or environment variables, create a `.env` file in the root directory (where `manage.py` is located).

Example:

```env
SECRET_KEY=your-django-secret-key
AI_API_KEY=your-api-key
```

Use the actual variable names expected by your project configuration.

### 5. Apply Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Generate Sample Data (Optional)

If the custom management command is included in your project, run:

```bash
python manage.py create_test_data
```

This generates sample data for testing the application's features.

### 7. Create an Admin Account

```bash
python manage.py createsuperuser
```

Follow the instructions to create your administrator account.

### 8. Run the Development Server

```bash
python manage.py runserver
```

Open your browser:

- **Application:** http://127.0.0.1:8000/
- **Django Admin:** http://127.0.0.1:8000/admin/

---

## 📖 Application Workflow

1. **User Registration/Login:** Employees and support staff access the application through authentication.
2. **Ticket Creation:** Employees submit technical issues with relevant details and attachments.
3. **Ticket Assignment:** Support staff review and manage incoming tickets.
4. **Issue Resolution:** Support staff communicate with employees, update ticket statuses, and resolve issues.
5. **Notifications:** Users receive updates about ticket activities.
6. **Analytics:** Administrators and support staff can review ticket statistics and reports.

---

## 🔮 Future Enhancements

- Email notifications for ticket updates.
- Export reports in CSV and PDF formats.
- SLA tracking and resolution countdowns.
- Advanced AI-powered ticket classification.
- Improved analytics and performance monitoring.

---

## 👩‍💻 Author

**Meenal Shelar**

- **GitHub:** [meenal-04](https://github.com/meenal-04)
- **LinkedIn:** [Meenal Shelar](https://linkedin.com/in/meenalshelar)

---

## ⭐ Support

If you find this project useful, consider giving the repository a star!

**Built with Python and Django.**
