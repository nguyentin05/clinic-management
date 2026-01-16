# Clinic Management

Hệ thống quản lý phòng khám được xây dựng dựa trên Django Rest Framework.

## 🚀 Tech Stack

Dự án sử dụng các công nghệ và dịch vụ hiện đại sau:

**Core & Backend:**
* **Framework:** Django
* **Database:** MySQL
* **Caching & Message Broker:** Redis
* **Async Tasks:** Celery

**Frontend & Mobile Integration (API):**
* **Notifications:** Firebase & WebSockets (Real-time updates)

**Infrastructure & DevOps:**
* **Containerization:** Docker & Docker Compose
* **CI/CD:** GitHub Actions (Deploy to PythonAnywhere)

**Third-party Services:**
* **Storage:** Cloudinary
* **Authentication:** Google OAuth2
* **Payment Gateways:**
    * MoMo
    * Stripe
    * VNPay

---

## 📂 Cấu trúc dự án

Dựa trên kiến trúc *Domain-Driven Design*, cấu trúc thư mục chính của dự án như sau:

```text
clinic-management/
├── .github/
├── apps/
│   ├── clinic/
│   ├── medical/
│   ├── notifications/
│   ├── payment/
│   ├── pharmacy/
│   └── users/
├── clinic_management/
├── templates/
│   └── admin/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env
├── firebase-credentials.json
└── manage.py
```
[🔗 Link báo cáo](https://docs.google.com/document/d/1Y04beecq-cN7KsIOiicAEbM45gO1Br9q6KGfvgCJ2mM/edit?usp=sharing)
 
[🔗 Link web](https://trongtin2005.pythonanywhere.com/)(có thể lúc bạn xem nó đã die do kinh phí ko cho phép:D)