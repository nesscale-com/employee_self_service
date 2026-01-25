<div align="center">
  <h1>Nesscale ESS</h1>
  <p><strong>Employee Self Service - Empower Your Workforce with Modern HR Self-Service</strong></p>
  
  [![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
  [![Frappe](https://img.shields.io/badge/Frappe-Framework-orange.svg)](https://frappeframework.com)
  
  <p>
    <a href="#features">Features</a> •
    <a href="#installation">Installation</a> •
    <a href="#usage">Usage</a> •
    <a href="#support">Support</a>
  </p>
</div>

---

## 🚀 Overview

**Nesscale ESS** is a comprehensive solution that extends the power of ERPNext to mobile devices. This repository contains the **open-source backend/server component** that integrates with ERPNext and HRMS to provide APIs and server-side functionality for the mobile application.

The **Nesscale ESS mobile app** (available for iOS and Android) connects to this backend, enabling employees to access HR and business operations anytime, anywhere—streamlining processes and boosting efficiency.

📱 **Download Mobile App:**
- [iOS App Store](https://apps.apple.com/app/nesscale-ess/id6450770577)
- [Google Play Store](https://play.google.com/store/apps/details?id=com.nesscale.ess)

🌐 **[Learn More](https://ess.nesscale.app)** | 📧 **[Contact Us](mailto:info@nesscale.com)**

> **Trusted by 100+ clients** • **10k+ downloads** • **4.8★ rating**

---

## ✨ Features

### 📱 HR & Payroll
- **Leave Management** - Apply for leaves, view balance, and track approvals
- **Attendance** - Check-in/check-out with geo-fencing support
- **Offline Attendance** - Mark attendance even without internet connection
- **Shift Attendance** - Manage shift schedules and attendance
- **Attendance Requests** - Submit and approve attendance regularization requests
- **Expense Claims** - Submit and track expense reimbursements
- **Payroll** - View salary slips and payroll details
- **Monthly Attendance** - Complete attendance history and reports

### 💼 Sales & CRM
- **Sales Orders** - Create and manage sales orders on the go
- **Quotations** - Generate quotations for customers
- **Customer Visits** - Track and manage customer visit schedules

### 📋 Task & Project Management
- **Task Assignment** - Assign and track tasks with deadlines
- **Project Tracking** - Monitor project progress effortlessly
- **Workflow Approvals** - Approve ERPNext workflows directly from the app

### 🤝 Collaboration
- **Posts & Updates** - Share updates with team members
- **Polls** - Create and participate in employee polls
- **Push Notifications** - Dynamically configurable real-time alerts

### 🌍 Advanced Features
- **Geo-Fencing** - Location-based attendance restrictions for compliance
- **Multilingual Support** - Use the app in your preferred language
- **Biometric Authentication** - Secure access with fingerprint/face recognition
- **Customizable Appearance** - Personalize the app interface
- **Manager Approvals** - Streamlined approval workflows for managers

---

## 📦 Installation

> **Note:** This installation is for the **backend/server component**. After installing this on your ERPNext server, employees can connect using the mobile apps available on [iOS App Store](https://apps.apple.com/app/nesscale-ess/id6450770577) and [Google Play Store](https://play.google.com/store/apps/details?id=com.nesscale.ess).

### Prerequisites

Before installing Nesscale ESS, ensure you have:

| Requirement | Version | Description |
|------------|---------|-------------|
| **Frappe Framework** | Latest | Core framework for the application |
| **ERPNext** | Compatible | ERP system for business operations |
| **HRMS** | Compatible | Human Resource Management System |

### Quick Start

1. **Get the App**

   Choose the appropriate branch for your Frappe version:

   ```bash
   # For Frappe/ERPNext version 13
   bench get-app https://github.com/nesscale-com/employee_self_service.git --branch version-13
   
   # For Frappe/ERPNext version 14
   bench get-app https://github.com/nesscale-com/employee_self_service.git --branch version-14
   
   # For Frappe/ERPNext version 15
   bench get-app https://github.com/nesscale-com/employee_self_service.git --branch version-15
   
   # For Frappe/ERPNext version 16
   bench get-app https://github.com/nesscale-com/employee_self_service.git --branch version-16
   ```

2. **Install on Site**

   ```bash
   bench --site [your-site-name] install-app employee_self_service
   ```

3. **Migrate Database**

   ```bash
   bench --site [your-site-name] migrate
   ```

4. **Restart Services**

   ```bash
   bench restart
   ```

### Post-Installation Setup

1. Navigate to **Setup > Employee Self Service Settings**
2. Configure permissions and access controls
3. Set up notification preferences
4. Customize the portal according to your organization's needs

---

## 💡 Usage

### For Employees

**Using the Mobile App:**
1. Download the Nesscale ESS mobile app:
   - [iOS App Store](https://apps.apple.com/app/nesscale-ess/id6450770577)
   - [Google Play Store](https://play.google.com/store/apps/details?id=com.nesscale.ess)
2. Login with your ERPNext credentials
3. Access your personal dashboard
4. Use the app to manage leaves, attendance, tasks, and more

**Using the Web Portal:**
1. Login to your Frappe site
2. Navigate to the **Nesscale ESS** module
3. Access your personal dashboard
4. Use the navigation menu to access different features

### For HR Administrators

1. Configure employee access and permissions
2. Set up approval workflows
3. Monitor employee requests and activities
4. Generate reports and analytics

---

## 🎯 Compatibility Matrix

| Branch | Frappe Version | ERPNext Version | Status |
|--------|---------------|-----------------|--------|
| version-13 | 13.x | 13.x | Stable |
| version-14 | 14.x | 14.x | Stable |
| version-15 | 15.x | 15.x | Stable |
| version-16 | 16.x | 16.x | Active Development |

---

## � Mobile Applications

The Nesscale ESS mobile apps provide a native mobile experience for iOS and Android devices.

### Download the Apps

<div align="center">
  
[![Download on App Store](https://img.shields.io/badge/Download_on-App_Store-black?style=for-the-badge&logo=apple&logoColor=white)](https://apps.apple.com/app/nesscale-ess/id6450770577)
[![Get it on Google Play](https://img.shields.io/badge/Get_it_on-Google_Play-black?style=for-the-badge&logo=google-play&logoColor=white)](https://play.google.com/store/apps/details?id=com.nesscale.ess)

</div>

### Requirements
- iOS 13.0 or later / Android 6.0 or later
- Active ERPNext installation with Nesscale ESS backend installed
- Internet connection (offline attendance supported)

**Note:** The mobile applications are proprietary software. This repository contains only the open-source backend component.

---

## �🛠️ Configuration

### Initial Setup

Access the Nesscale ESS settings from:
```
Home > Setup > Employee Self Service Settings
```

### Key Configuration Options

- **Portal Access**: Define which employees can access the portal
- **Approval Workflows**: Configure multi-level approval processes
- **Notifications**: Set up email and in-app notification preferences
- **Document Permissions**: Control document visibility and access rights


---

## 🤝 Support

We're here to help you succeed with Nesscale ESS!

### Get Help

- 📧 **Email Support**: [info@nesscale.com](mailto:info@nesscale.com)
- 🌐 **Website**: [https://ess.nesscale.app](https://ess.nesscale.app)
- 🐛 **Issue Tracker**: [GitHub Issues](https://github.com/nesscale-com/employee_self_service/issues)

### Enterprise Support

For enterprise customers, we offer:
- Priority support with guaranteed response times
- Custom feature development
- Training and onboarding assistance
- Dedicated account management

📧 Contact us at [info@nesscale.com](mailto:info@nesscale.com) for enterprise inquiries.

---


## 📄 License

**Backend Component (This Repository):** The Nesscale ESS backend/server component is free and open-source software licensed under the **GNU General Public License v3.0**. You can freely use, modify, and distribute this software. See the [LICENSE](LICENSE) file for complete details.

**Mobile Applications:** The Nesscale ESS mobile applications (iOS and Android) are proprietary software and are not covered by this open-source license.

---

## 🙏 Acknowledgments

Built with ❤️ using:
- [Frappe Framework](https://frappeframework.com)
- [ERPNext](https://erpnext.com)
- [HRMS](https://github.com/frappe/hrms)

---

## 📞 About Nesscale

**Nesscale** is committed to building innovative business solutions that help organizations streamline their operations and empower their workforce.

- 🌐 **Website**: [nesscale.com](https://nesscale.com)
- 📧 **Email**: [info@nesscale.com](mailto:info@nesscale.com)
- 🔗 **LinkedIn**: Follow us for updates and insights

---

<div align="center">
  <p>Made with ❤️ by <strong>Nesscale</strong></p>
  <p>
    <a href="https://ess.nesscale.app">Website</a> •
    <a href="mailto:info@nesscale.com">Contact</a> •
    <a href="https://github.com/nesscale-com/employee_self_service">GitHub</a>
  </p>
</div>
