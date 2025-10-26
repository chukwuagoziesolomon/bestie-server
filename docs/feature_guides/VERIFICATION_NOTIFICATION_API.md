# 📋 Verification Notification System API

## 🚀 Overview

The verification notification system automatically sends notifications to vendors and couriers when their verification status changes through multiple channels:
- **WhatsApp** (via Twilio/WhatsApp Business API)
- **WebSocket** (real-time in-app notifications)
- **Email** (detailed status information)

## 📋 API Endpoints

### **1. Vendor Verification Status**

**GET** `/api/user/vendors/verification-status/`

**Response:**
```json
{
  "status": "pending",
  "verified": false,
  "message": "Your vendor application is under review.",
  "notes": null
}
```

### **2. Courier Verification Status**

**GET** `/api/user/couriers/verification-status/`

**Response:**
```json
{
  "success": true,
  "data": {
    "courier_id": 123,
    "user_id": 456,
    "full_name": "John Doe",
    "email": "john@example.com",
    "phone": "+2348123456789",
    "verification_status": "pending",
    "verified": false,
    "verification_date": null,
    "verification_notes": null,
    "verification_preference": "NIN",
    "message": "Your courier application is under review. We will notify you once the review is complete.",
    "next_steps": [
      "Wait for review completion (usually within 24-48 hours)",
      "Ensure all documents are clear and valid",
      "Check your email and phone for updates"
    ],
    "required_documents": [
      {
        "name": "Government-issued ID",
        "type": "NIN, Driver's License, or International Passport",
        "required": true,
        "description": "Clear photo of your valid government-issued identification"
      },
      {
        "name": "Proof of Address",
        "type": "Utility Bill or Bank Statement",
        "required": true,
        "description": "Recent utility bill or bank statement (not older than 3 months)"
      },
      {
        "name": "Vehicle Registration",
        "type": "Vehicle Documents",
        "required": true,
        "description": "Valid vehicle registration documents if using a vehicle"
      },
      {
        "name": "Driver's License",
        "type": "Valid Driver's License",
        "required": true,
        "description": "Valid driver's license if using a vehicle for delivery"
      },
      {
        "name": "Profile Photo",
        "type": "Clear Headshot",
        "required": true,
        "description": "Clear, professional headshot photo"
      }
    ],
    "support_contact": {
      "email": "support@bestyy.com",
      "phone": "+234-XXX-XXXX",
      "whatsapp": "+234-XXX-XXXX"
    }
  }
}
```

### **3. Courier Verification History**

**GET** `/api/user/couriers/verification-history/`

**Response:**
```json
{
  "success": true,
  "data": {
    "courier_id": 123,
    "current_status": "pending",
    "application_date": "2025-09-12T10:00:00Z",
    "verification_date": null,
    "timeline": [
      {
        "date": "2025-09-12T10:00:00Z",
        "status": "submitted",
        "title": "Application Submitted",
        "description": "Your courier application was submitted for review",
        "icon": "📋"
      },
      {
        "date": null,
        "status": "estimated",
        "title": "Estimated Review Completion",
        "description": "Your application will be reviewed within 24-48 hours",
        "icon": "⏰"
      }
    ],
    "verification_notes": null,
    "estimated_review_time": "24-48 hours"
  }
}
```

## 🔔 Verification Notification Channels

### **1. WhatsApp Notifications**

**Service**: `VerificationNotificationService.send_verification_notification()`

#### **Approval Message (Vendor):**
```
🎉 *CONGRATULATIONS!*

Your vendor account has been *APPROVED* on Bestyy!

🏪 *Business:* Burger Palace
✅ *Status:* VERIFIED & APPROVED
📅 *Date:* September 12, 2025

🚀 *What's Next?*
• Your restaurant is now live on Bestyy
• Customers can find and order from you
• Complete your menu setup
• Start receiving orders immediately

📱 *Quick Setup:*
1. Upload your menu items
2. Add high-quality food photos
3. Set delivery areas
4. Configure payment settings

💡 *Pro Tips:*
• Keep menu updated and accurate
• Respond quickly to orders
• Maintain high food quality
• Use attractive food photos

📞 *Need Help?*
Contact us:
• Email: support@bestyy.com
• Phone: +234-XXX-XXXX

Welcome to the Bestyy family! 🍽️

---
*Bestyy - Food Delivery Platform*
```

#### **Approval Message (Courier):**
```
🎉 *CONGRATULATIONS!*

Your courier account has been *APPROVED* on Bestyy!

👤 *Name:* John Doe
✅ *Status:* VERIFIED & APPROVED
📅 *Date:* September 12, 2025

🚀 *What's Next?*
• Download the Bestyy Courier app
• Complete your profile setup
• Set your availability schedule
• Start accepting delivery requests

📱 *Quick Setup:*
1. visit our website 
2. Set your working hours
3. Choose delivery areas
4. Update your vehicle info

💡 *Pro Tips:*
• Always be professional
• Keep your vehicle in good condition
• Communicate clearly with customers
• Deliver orders on time

📞 *Need Help?*
Contact us:
• Email: support@bestyy.com
• Phone: +234-XXX-XXXX

Welcome to the Bestyy delivery team! 🚚

---
*Bestyy - Food Delivery Platform*
```

#### **Rejection Message (Vendor):**
```
📋 *Vendor Application Update*

Dear Burger Palace,

Thank you for your interest in joining Bestyy as a vendor partner.

❌ *Status:* NOT APPROVED
📅 *Date:* September 12, 2025

📝 *Reason:*
Your business registration documents are not clear enough. Please provide clearer photos of your business registration certificate.

🔄 *Next Steps:*
• Review the feedback above
• Address any issues mentioned
• Update your application
• Resubmit with correct information

📞 *Need Clarification?*
Contact us:
• Email: support@bestyy.com
• Phone: +234-XXX-XXXX

We encourage you to reapply once you address the concerns mentioned above.

Best regards,
Bestyy Team

---
*Bestyy - Food Delivery Platform*
```

### **2. WebSocket Notifications**

**Service**: `VerificationNotificationService._send_websocket_notification()`

**Connection URL**: 
- Vendors: `ws://localhost:8000/ws/vendor/`
- Couriers: `ws://localhost:8000/ws/courier/`

**Message Format:**
```json
{
  "type": "verification_notification",
  "data": {
    "type": "verification.status_changed",
    "user_type": "vendor",
    "status": "approved",
    "business_name": "Burger Palace",
    "admin_notes": null,
    "timestamp": "2025-09-12T16:30:00Z"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "WebSocket verification notification sent successfully"
}
```

### **3. Email Notifications**

**Service**: `VerificationNotificationService._send_email_notification()`

#### **Approval Email Subject**: `✅ Vendor Account Approved - Bestyy`

#### **Approval Email Body (Vendor):**
```
🎉 Congratulations! Your Vendor Account Has Been Approved!

Dear Burger Palace,

We are excited to inform you that your vendor account has been successfully verified and approved on Bestyy!

✅ *Account Status: APPROVED*
📅 *Approval Date: September 12, 2025 at 4:30 PM*

🚀 *What's Next?*
- Your restaurant is now live on Bestyy platform
- Customers can now find and order from your establishment
- You can access all vendor dashboard features
- Start receiving orders immediately

📱 *Quick Actions:*
1. Complete your menu setup
2. Upload high-quality food images
3. Set your delivery areas and timing
4. Configure your payment settings

💡 *Pro Tips for Success:*
- Keep your menu updated and accurate
- Respond quickly to customer orders
- Maintain high food quality standards
- Use attractive food photography

📞 *Need Help?*
Our support team is here to assist you. Contact us through:
- Email: support@bestyy.com
- Phone: +234-XXX-XXXX
- In-app chat support

Welcome to the Bestyy family! We're excited to partner with you in delivering amazing food experiences to our customers.

Best regards,
The Bestyy Team

---
This is an automated notification. For support, contact us through the Bestyy platform.
```

#### **Rejection Email Subject**: `❌ Vendor Account Application Update - Bestyy`

#### **Rejection Email Body (Vendor):**
```
📋 Vendor Account Application Update

Dear Burger Palace,

Thank you for your interest in joining Bestyy as a vendor partner. After reviewing your application, we regret to inform you that your vendor account application was not approved at this time.

❌ *Account Status: NOT APPROVED*
📅 *Review Date: September 12, 2025 at 4:30 PM*

📝 *Reason for Rejection:*
Your business registration documents are not clear enough. Please provide clearer photos of your business registration certificate.

🔄 *Next Steps:*
- Review the feedback provided above
- Address any issues mentioned
- Resubmit your application with updated information
- Ensure all required documents are clear and valid

📞 *Need Clarification?*
Our support team is available to help you understand the requirements better:
- Email: support@bestyy.com
- Phone: +234-XXX-XXXX
- In-app chat support

We encourage you to reapply once you have addressed the concerns mentioned above. We look forward to potentially welcoming you to the Bestyy platform in the future.

Best regards,
The Bestyy Team

---
This is an automated notification. For support, contact us through the Bestyy platform.
```

## 🎯 Frontend Implementation

### **1. WebSocket Connection for Verification Notifications**

```javascript
// Connect to vendor WebSocket
const vendorSocket = new WebSocket('ws://localhost:8000/ws/vendor/');

vendorSocket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    if (data.type === 'verification_notification') {
        showVerificationNotification(data.data);
    }
};

function showVerificationNotification(notificationData) {
    const { user_type, status, business_name, admin_notes } = notificationData;
    
    let title, message, icon, color;
    
    if (status === 'approved') {
        title = '🎉 Account Approved!';
        message = `Congratulations! Your ${user_type} account has been approved.`;
        icon = '✅';
        color = 'success';
    } else if (status === 'rejected') {
        title = '❌ Application Update';
        message = `Your ${user_type} application was not approved. Check the details below.`;
        icon = '❌';
        color = 'error';
    } else {
        title = '📋 Status Update';
        message = `Your ${user_type} account status has been updated.`;
        icon = '📋';
        color = 'info';
    }
    
    // Show notification popup
    const notification = document.createElement('div');
    notification.className = `verification-notification ${color}`;
    notification.innerHTML = `
        <div class="notification-header">
            <h3>${icon} ${title}</h3>
            <button onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
        <div class="notification-body">
            <p>${message}</p>
            ${admin_notes ? `<p><strong>Notes:</strong> ${admin_notes}</p>` : ''}
        </div>
        <div class="notification-actions">
            <button onclick="viewVerificationStatus()">View Status</button>
            ${status === 'rejected' ? '<button onclick="resubmitApplication()">Resubmit</button>' : ''}
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 15 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 15000);
}
```

### **2. Check Verification Status**

```javascript
// Check vendor verification status
async function checkVendorVerificationStatus() {
    try {
        const response = await fetch('/api/user/vendors/verification-status/', {
            headers: {
                'Authorization': `Bearer ${vendorToken}`
            }
        });
        
        const data = await response.json();
        
        if (data.verified) {
            showSuccessMessage('Your account is verified and approved!');
        } else {
            showInfoMessage(`Status: ${data.status}. ${data.message}`);
        }
    } catch (error) {
        console.error('Error checking verification status:', error);
    }
}

// Check courier verification status
async function checkCourierVerificationStatus() {
    try {
        const response = await fetch('/api/user/couriers/verification-status/', {
            headers: {
                'Authorization': `Bearer ${courierToken}`
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            const statusData = data.data;
            updateVerificationUI(statusData);
        }
    } catch (error) {
        console.error('Error checking verification status:', error);
    }
}

function updateVerificationUI(statusData) {
    const statusElement = document.getElementById('verification-status');
    const messageElement = document.getElementById('verification-message');
    const nextStepsElement = document.getElementById('next-steps');
    
    statusElement.textContent = statusData.verification_status;
    statusElement.className = `status-${statusData.verification_status}`;
    messageElement.textContent = statusData.message;
    
    // Update next steps
    nextStepsElement.innerHTML = statusData.next_steps
        .map(step => `<li>${step}</li>`)
        .join('');
}
```

### **3. Verification History Timeline**

```javascript
// Load verification history
async function loadVerificationHistory() {
    try {
        const response = await fetch('/api/user/couriers/verification-history/', {
            headers: {
                'Authorization': `Bearer ${courierToken}`
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            renderTimeline(data.data.timeline);
        }
    } catch (error) {
        console.error('Error loading verification history:', error);
    }
}

function renderTimeline(timeline) {
    const timelineElement = document.getElementById('verification-timeline');
    
    timelineElement.innerHTML = timeline.map(item => `
        <div class="timeline-item ${item.status}">
            <div class="timeline-icon">${item.icon}</div>
            <div class="timeline-content">
                <h4>${item.title}</h4>
                <p>${item.description}</p>
                ${item.date ? `<small>${new Date(item.date).toLocaleString()}</small>` : ''}
            </div>
        </div>
    `).join('');
}
```

## 🔧 Admin Integration

### **Triggering Verification Notifications**

When admins approve or reject applications, the system automatically sends notifications:

```python
# In admin views when status changes
from user.services.verification_notification_service import VerificationNotificationService

# When approving a vendor
vendor.verification_status = 'approved'
vendor.verification_date = timezone.now()
vendor.save()

# Send notification
notification_results = VerificationNotificationService.send_verification_notification(
    user_type='vendor',
    user_profile=vendor,
    old_status='pending',
    new_status='approved',
    admin_notes=None
)

# When rejecting a courier
courier.verification_status = 'rejected'
courier.verification_date = timezone.now()
courier.verification_notes = 'Invalid identification document'
courier.save()

# Send notification
notification_results = VerificationNotificationService.send_verification_notification(
    user_type='courier',
    user_profile=courier,
    old_status='pending',
    new_status='rejected',
    admin_notes='Invalid identification document'
)
```

## 📊 Notification Status Tracking

### **Success Response Example:**
```json
{
  "notifications": {
    "whatsapp": {
      "success": true,
      "message": "Verification notification sent to +2348123456789",
      "vendor_phone": "+2348123456789",
      "status": "approved",
      "service_type": "twilio"
    },
    "websocket": {
      "success": true,
      "message": "WebSocket verification notification sent successfully"
    },
    "email": {
      "success": true,
      "message": "Email sent to vendor@burgerpalace.com",
      "user_email": "vendor@burgerpalace.com"
    }
  }
}
```

## 🚀 Key Features

### **✅ Automatic Notifications**
- **Multi-channel**: WhatsApp, WebSocket, Email
- **Real-time**: Instant notifications via WebSocket
- **Detailed**: Comprehensive status information
- **User-friendly**: Clear next steps and support contact

### **✅ Status Management**
- **Vendor Status**: pending, approved, rejected
- **Courier Status**: pending, approved, rejected, suspended, incomplete
- **History Tracking**: Complete verification timeline
- **Document Requirements**: Clear list of required documents

### **✅ Frontend Integration**
- **WebSocket**: Real-time status updates
- **Status Checking**: API endpoints for current status
- **History View**: Timeline of verification progress
- **User Guidance**: Next steps and support information

The verification notification system ensures users are always informed about their application status and know exactly what to do next! 🎉






