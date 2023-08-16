# Employee Self Service

## Description

Employee Self-Service is a Frappe app that allows employees to access and manage their own HR-related information and perform various self-service tasks. This app requires ERPNext and HRMS to be installed and running. Additionally, the chat feature of Frappe (Frappe's Chat application) is required for certain functionalities.

## Installation

1. **Prerequisites**

   Before installing the Employee Self-Service app, make sure you have the following requirements met:
   - Frappe framework is installed and set up on your system.
   - ERPNext and HRMS are installed and configured.

2. **Install the App**

   Run the following commands to install the Employee Self-Service app:<br/>
- <b>bench get-app https://github.com/nesscale-com/employee_self_service.git --branch version-14</b><br/>
- <b>bench --site <site_name> install-app employee_self_service</b>



Note: Replace `<site_name>` with the name of your Frappe site.

3. **Run Bench Migrate**

After the installation, run the following command to migrate the database:

bench migrate



## License

Employee Self Service is distributed under the GNU/General Public License. See the LICENSE file for more information.

## Support and Contact

For any issues, questions, or feedback, please feel free to reach out via email: [info@nesscale.com](mailto:your_info@nesscale.com)
