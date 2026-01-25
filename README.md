<div align="center">
  <h1>Nesscale ESS</h1>
  <p>Employee Self Service for ERPNext</p>
  
  [![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
  [![Frappe](https://img.shields.io/badge/Frappe-Framework-orange.svg)](https://frappeframework.com)
  
  <p>
    <a href="https://apps.apple.com/app/nesscale-ess/id6450770577">iOS App</a> •
    <a href="https://play.google.com/store/apps/details?id=com.nesscale.ess">Android App</a> •
    <a href="https://ess.nesscale.app">Website</a>
  </p>
</div>

---

## What is this?

This is the backend component for Nesscale ESS - a mobile app that brings ERPNext to your phone. Employees can manage their HR tasks, sales activities, and projects right from their mobile devices.

**This repo is open source** (GPL v3.0) and provides the server-side APIs. The mobile apps are available separately on the App Store and Play Store.

📱 **Download the mobile app:**
- [iOS App Store](https://apps.apple.com/app/nesscale-ess/id6450770577)
- [Google Play Store](https://play.google.com/store/apps/details?id=com.nesscale.ess)

> Trusted by 100+ clients • 10k+ downloads • 4.8★ rating

---

## Features

**HR & Attendance**
- Apply for leaves and track approvals
- Check-in/check-out with geo-fencing
- Offline attendance support
- View salary slips and attendance history
- Submit expense claims

**Sales & CRM**
- Create sales orders and quotations
- Manage customer visits
- Track sales activities

**Tasks & Projects**
- Assign and manage tasks
- Track project progress
- Approve workflows on the go

**Other Features**
- Real-time push notifications
- Multilingual support
- Biometric authentication
- Posts, polls, and team updates

---

## Installation

You need ERPNext and HRMS installed on your server. Then:

**1. Get the app**

```bash
# For version 13
bench get-app https://github.com/nesscale-com/employee_self_service.git --branch version-13

# For version 14
bench get-app https://github.com/nesscale-com/employee_self_service.git --branch version-14

# For version 15
bench get-app https://github.com/nesscale-com/employee_self_service.git --branch version-15

# For version 16
bench get-app https://github.com/nesscale-com/employee_self_service.git --branch version-16
```

**2. Install on your site**

```bash
bench --site [your-site-name] install-app employee_self_service
bench --site [your-site-name] migrate
bench restart
```

**3. Configure**

Go to **Setup > Employee Self Service Settings** in your ERPNext desk and configure permissions and notifications.

**4. Connect mobile app**

Download the mobile app and login with your ERPNext credentials. That's it!

---

## Version Compatibility

| Branch | Frappe/ERPNext Version |
|--------|----------------------|
| version-13 | 13.x |
| version-14 | 14.x |
| version-15 | 15.x |
| version-16 | 16.x (latest) |

---

## Support

Need help? We're here for you:

- 📧 Email: [info@nesscale.com](mailto:info@nesscale.com)
- 🌐 Website: [ess.nesscale.app](https://ess.nesscale.app)
- 🐛 Issues: [GitHub Issues](https://github.com/nesscale-com/employee_self_service/issues)

For enterprise support, custom features, or training, drop us an email.

---

## Contributing

We welcome contributions! Feel free to:
- Report bugs or suggest features via GitHub Issues
- Submit pull requests
- Help improve documentation

---

## License

**Backend (this repo):** Open source under GPL v3.0 - use it freely, modify it, share it.

**Mobile apps:** Proprietary software - see [Terms of Service](https://ess.nesscale.app/terms)

---

## About

Built with ❤️ by [Nesscale](https://nesscale.com) using the Frappe Framework.

We build practical solutions that make ERPNext more accessible and easier to use for everyday tasks.

---

<div align="center">
  <p>
    <a href="https://ess.nesscale.app">Website</a> •
    <a href="mailto:info@nesscale.com">Contact</a> •
    <a href="https://github.com/nesscale-com/employee_self_service">GitHub</a>
  </p>
</div>
