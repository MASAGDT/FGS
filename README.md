# Franchise Governance System (FGS)
A prototype implementation of a **Franchise-Based Cooperative Governance System**.  
FGS is a civic simulation framework demonstrating how a decentralized, non-governmental,
voluntary citizenship model can operate with:

- Franchise Units (FUs)
- Regional & national population structures
- A citizen oath & onboarding flow
- Household structures
- Dues & benefits tracking
- Role-based authority (NC/FU Officers, Treasury Stewards, ASA Liaisons)
- OAuth2 login via PayPal (sandbox)

This prototype is designed for:
- Research  
- Public analysis  
- Governance modeling  
- Future expansion into a fully-distributed, legally-aligned civic platform  

---

## 🚀 Features

### **Core System**
- Citizen creation via PayPal OAuth2 login  
- Oath acceptance & onboarding  
- Household creation & membership tracking  
- Regional → Country → Franchise Unit hierarchy  
- Role-based access control (RBAC)  
- Admin panel for user management  

### **Treasury Mechanics**
- Track:
  - Dues paid  
  - Benefits received  
  - FU-level monthly aggregates  
- Treasury roles:
  - **TREASURY_STEWARD**  
  - **ASA_LIAISON**

### **Architecture**
- Flask backend  
- SQLAlchemy ORM  
- OAuth2 via Authlib  
- SQLite (default)  
- `.env` configuration support  
- Modular design for future expansion into:
  - Flask Blueprints  
  - Microservices  
  - Federated governance nodes  

---

## 🛠 Installation

### Clone the repository:
```bash
git clone https://github.com/MASAGDT/FGS.git
cd FGS
```

### Create virtual environment & install dependencies:
```bash
python -m venv venv
source venv/Scripts/activate  # Windows
pip install -r requirements.txt
```

### Create `.env` file:
```bash
cp .env.example .env
```

Modify with your PayPal sandbox credentials.

---

## 🔐 Environment Variables

| Variable | Description |
|---------|-------------|
| `SECRET_KEY` | Flask session key |
| `PAYPAL_ENV` | `sandbox` or `live` |
| `PAYPAL_CLIENT_ID` | PayPal app client ID |
| `PAYPAL_CLIENT_SECRET` | PayPal app secret |
| `DATABASE_URL` | SQLAlchemy DB URI |

Example `.env` is included as `.env.example`.

---

## 🗄 Initialize the Database

```bash
flask init-db
```

This will:
- Create base tables  
- Seed world → US → Franchise Unit  
- Seed default roles  
- Promote the first user to **admin**  

---

## ▶ Run the Server

```bash
python app.py
```

App runs at:

```
http://localhost:5000
```

---

## 📘 Documentation

FGS includes:
- Governance architecture notes
- Role definitions
- Treasury SOP
- Oath text
- Population model

Documentation will expand as research continues.

---

## 📜 License

Licensed under the **MIT License**.  
See the `LICENSE` file for details.

---

## 🤝 Contributions

All research, forks, and experimental governance models are welcome.  
Submit issues or PRs to extend the framework.

---

## 🌐 Project Origin

FGS is part of a broader research effort within the  
**Modular AI Service Architecture GPT Dream Team Cooperative (MASAGDTC)**  
to model voluntary, scalable, globally-aligned governance systems using  
transparent, auditable, and mathematically constrained structures.

