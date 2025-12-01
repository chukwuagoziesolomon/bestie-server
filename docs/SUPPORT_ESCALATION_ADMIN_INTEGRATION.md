# Support Escalation Admin Dashboard Integration Guide

## Overview
This guide shows how to integrate the Support Escalation system into your admin dashboard frontend. The system automatically logs customer complaints from WhatsApp and provides a complete interface for customer support management.

## API Endpoints

### Base URL
```
/api/user/admin/
```

### Available Endpoints

#### 1. Get Support Escalations
```http
GET /api/user/admin/support-escalations/
```

**Query Parameters:**
- `status` (optional): Filter by resolution status (`pending`, `in_progress`, `contacted`, `resolved`)
- `severity` (optional): Filter by severity (`urgent`, `high`, `medium`, `low`)
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 20)

**Response:**
```json
{
  "success": true,
  "escalations": [
    {
      "id": 1,
      "customer_phone": "+2348123456789",
      "customer_name": "John Doe",
      "trigger_type": "Food Quality Complaint",
      "description": "The food was cold and tasteless...",
      "severity_level": "high",
      "severity_display": "🔴 High Priority",
      "resolution_status": "pending",
      "status_display": "Pending",
      "assigned_agent": {
        "id": 5,
        "name": "Agent Smith",
        "email": "agent@company.com"
      },
      "contact_attempts": 0,
      "last_contact_attempt": null,
      "contact_successful": false,
      "should_contact": true,
      "contact_info": {
        "phone": "+2348123456789",
        "name": "John Doe",
        "preferred_method": "whatsapp",
        "last_contact": null
      },
      "escalation_reason": "Food quality complaint requiring immediate attention",
      "context_data": {
        "complaint_message": "Original complaint text...",
        "complaint_type": "food_quality"
      },
      "created_at": "2025-12-01T10:30:00Z",
      "updated_at": "2025-12-01T10:30:00Z",
      "resolved_at": null,
      "resolved_by": null,
      "resolution_notes": null
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 50,
    "pages": 3
  },
  "statistics": {
    "total": 50,
    "pending": 15,
    "in_progress": 8,
    "urgent": 3,
    "high": 12,
    "requires_contact": 20
  }
}
```

#### 2. Get Escalation Details
```http
GET /api/user/admin/support-escalations/{escalation_id}/
```

**Response includes conversation history:**
```json
{
  "success": true,
  "escalation": {
    // ... all fields from above
    "conversation_history": [
      {
        "content": "I want to order jollof rice",
        "timestamp": "2025-12-01T10:00:00Z",
        "message_type": "text",
        "direction": "incoming"
      },
      {
        "content": "The food was terrible!",
        "timestamp": "2025-12-01T10:25:00Z",
        "message_type": "text",
        "direction": "incoming"
      }
    ]
  }
}
```

#### 3. Assign Agent to Escalation
```http
POST /api/user/admin/support-escalations/{escalation_id}/assign/
Content-Type: application/json

{
  "agent_id": 5
}
```

#### 4. Schedule Customer Contact
```http
POST /api/user/admin/support-escalations/{escalation_id}/schedule-contact/
Content-Type: application/json

{
  "contact_method": "whatsapp"
}
```

#### 5. Record Contact Attempt
```http
POST /api/user/admin/support-escalations/{escalation_id}/record-contact/
Content-Type: application/json

{
  "success": true,
  "notes": "Customer contacted successfully via WhatsApp. Issue resolved."
}
```

#### 6. Resolve Escalation
```http
POST /api/user/admin/support-escalations/{escalation_id}/resolve/
Content-Type: application/json

{
  "resolution_notes": "Customer complaint resolved. Provided full refund and fresh order."
}
```

#### 7. Get Support Agents
```http
GET /api/user/admin/support-agents/
```

**Response:**
```json
{
  "success": true,
  "agents": [
    {
      "id": 5,
      "name": "Agent Smith",
      "email": "agent@company.com",
      "workload": {
        "total_assigned": 10,
        "pending": 3,
        "in_progress": 2,
        "resolved_today": 5,
        "capacity_remaining": 0
      }
    }
  ]
}
```

## Frontend Integration Examples

### React Components

#### 1. Escalations Dashboard Component

```jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const EscalationsDashboard = () => {
  const [escalations, setEscalations] = useState([]);
  const [statistics, setStatistics] = useState({});
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    status: '',
    severity: '',
    page: 1
  });

  useEffect(() => {
    fetchEscalations();
  }, [filters]);

  const fetchEscalations = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filters.status) params.append('status', filters.status);
      if (filters.severity) params.append('severity', filters.severity);
      params.append('page', filters.page);

      const response = await axios.get(`/api/user/admin/support-escalations/?${params}`);
      setEscalations(response.data.escalations);
      setStatistics(response.data.statistics);
    } catch (error) {
      console.error('Error fetching escalations:', error);
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity) => {
    const colors = {
      urgent: 'bg-red-600 text-white',
      high: 'bg-red-500 text-white',
      medium: 'bg-yellow-500 text-white',
      low: 'bg-green-500 text-white'
    };
    return colors[severity] || 'bg-gray-500 text-white';
  };

  const getStatusColor = (status) => {
    const colors = {
      pending: 'bg-gray-500 text-white',
      in_progress: 'bg-blue-500 text-white',
      contacted: 'bg-purple-500 text-white',
      resolved: 'bg-green-600 text-white'
    };
    return colors[status] || 'bg-gray-400 text-white';
  };

  return (
    <div className="p-6">
      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-medium text-gray-500">Total Escalations</h3>
          <p className="text-2xl font-bold text-gray-900">{statistics.total}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-medium text-gray-500">Pending</h3>
          <p className="text-2xl font-bold text-orange-600">{statistics.pending}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-medium text-gray-500">In Progress</h3>
          <p className="text-2xl font-bold text-blue-600">{statistics.in_progress}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-medium text-gray-500">Urgent Priority</h3>
          <p className="text-2xl font-bold text-red-600">{statistics.urgent}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-medium text-gray-500">Requires Contact</h3>
          <p className="text-2xl font-bold text-purple-600">{statistics.requires_contact}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex flex-wrap gap-4">
          <select 
            value={filters.status} 
            onChange={(e) => setFilters({...filters, status: e.target.value, page: 1})}
            className="border rounded px-3 py-2"
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="in_progress">In Progress</option>
            <option value="contacted">Contacted</option>
            <option value="resolved">Resolved</option>
          </select>

          <select 
            value={filters.severity} 
            onChange={(e) => setFilters({...filters, severity: e.target.value, page: 1})}
            className="border rounded px-3 py-2"
          >
            <option value="">All Priorities</option>
            <option value="urgent">🚨 Urgent</option>
            <option value="high">🔴 High</option>
            <option value="medium">🟡 Medium</option>
            <option value="low">🟢 Low</option>
          </select>

          <button 
            onClick={() => setFilters({status: '', severity: '', page: 1})}
            className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
          >
            Clear Filters
          </button>
        </div>
      </div>

      {/* Escalations Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Customer
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Issue Type
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Priority
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Agent
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Contact
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {escalations.map((escalation) => (
              <tr key={escalation.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div>
                    <div className="text-sm font-medium text-gray-900">
                      {escalation.customer_name || 'Unknown'}
                    </div>
                    <div className="text-sm text-gray-500">
                      {escalation.customer_phone}
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">{escalation.trigger_type}</div>
                  <div className="text-sm text-gray-500 truncate max-w-xs">
                    {escalation.description}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getSeverityColor(escalation.severity_level)}`}>
                    {escalation.severity_display}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(escalation.resolution_status)}`}>
                    {escalation.status_display}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {escalation.assigned_agent ? escalation.assigned_agent.name : 'Unassigned'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">
                    {escalation.should_contact && (
                      <span className="text-red-600 font-semibold">📞 Contact Required</span>
                    )}
                    {escalation.contact_attempts > 0 && (
                      <div className="text-xs text-gray-500">
                        {escalation.contact_attempts} attempts
                      </div>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <button 
                    onClick={() => handleViewDetails(escalation.id)}
                    className="text-blue-600 hover:text-blue-900 mr-3"
                  >
                    View
                  </button>
                  {escalation.should_contact && (
                    <a 
                      href={`https://wa.me/${escalation.customer_phone.replace('+', '')}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-green-600 hover:text-green-900"
                    >
                      📱 WhatsApp
                    </a>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default EscalationsDashboard;
```

#### 2. Escalation Detail Modal Component

```jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const EscalationDetailModal = ({ escalationId, isOpen, onClose }) => {
  const [escalation, setEscalation] = useState(null);
  const [agents, setAgents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState('');
  const [contactNotes, setContactNotes] = useState('');
  const [resolutionNotes, setResolutionNotes] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isOpen && escalationId) {
      fetchEscalationDetails();
      fetchAgents();
    }
  }, [isOpen, escalationId]);

  const fetchEscalationDetails = async () => {
    try {
      const response = await axios.get(`/api/user/admin/support-escalations/${escalationId}/`);
      setEscalation(response.data.escalation);
      setSelectedAgent(response.data.escalation.assigned_agent?.id || '');
    } catch (error) {
      console.error('Error fetching escalation details:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAgents = async () => {
    try {
      const response = await axios.get('/api/user/admin/support-agents/');
      setAgents(response.data.agents);
    } catch (error) {
      console.error('Error fetching agents:', error);
    }
  };

  const handleAssignAgent = async () => {
    if (!selectedAgent) return;

    try {
      await axios.post(`/api/user/admin/support-escalations/${escalationId}/assign/`, {
        agent_id: parseInt(selectedAgent)
      });
      fetchEscalationDetails(); // Refresh data
      alert('Agent assigned successfully!');
    } catch (error) {
      console.error('Error assigning agent:', error);
      alert('Failed to assign agent');
    }
  };

  const handleScheduleContact = async () => {
    try {
      await axios.post(`/api/user/admin/support-escalations/${escalationId}/schedule-contact/`, {
        contact_method: 'whatsapp'
      });
      fetchEscalationDetails(); // Refresh data
      alert('Contact scheduled successfully!');
    } catch (error) {
      console.error('Error scheduling contact:', error);
      alert('Failed to schedule contact');
    }
  };

  const handleRecordContact = async (success) => {
    try {
      await axios.post(`/api/user/admin/support-escalations/${escalationId}/record-contact/`, {
        success: success,
        notes: contactNotes
      });
      setContactNotes('');
      fetchEscalationDetails(); // Refresh data
      alert('Contact attempt recorded!');
    } catch (error) {
      console.error('Error recording contact:', error);
      alert('Failed to record contact attempt');
    }
  };

  const handleResolve = async () => {
    if (!resolutionNotes.trim()) {
      alert('Resolution notes are required');
      return;
    }

    try {
      await axios.post(`/api/user/admin/support-escalations/${escalationId}/resolve/`, {
        resolution_notes: resolutionNotes
      });
      setResolutionNotes('');
      fetchEscalationDetails(); // Refresh data
      alert('Escalation resolved successfully!');
    } catch (error) {
      console.error('Error resolving escalation:', error);
      alert('Failed to resolve escalation');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen p-4">
        <div className="fixed inset-0 bg-black bg-opacity-50" onClick={onClose}></div>
        <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-screen overflow-y-auto relative">
          {loading ? (
            <div className="p-8 text-center">Loading...</div>
          ) : escalation ? (
            <div className="p-6">
              {/* Header */}
              <div className="flex justify-between items-start mb-6">
                <h2 className="text-2xl font-bold text-gray-900">
                  Escalation #{escalation.id}
                </h2>
                <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
                  ✕
                </button>
              </div>

              {/* Customer Info */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-900 mb-2">Customer Information</h3>
                  <p><strong>Name:</strong> {escalation.customer_name || 'Unknown'}</p>
                  <p><strong>Phone:</strong> {escalation.customer_phone}</p>
                  <p>
                    <strong>WhatsApp:</strong> 
                    <a 
                      href={`https://wa.me/${escalation.customer_phone.replace('+', '')}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-green-600 hover:underline ml-2"
                    >
                      📱 Open WhatsApp
                    </a>
                  </p>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-900 mb-2">Escalation Details</h3>
                  <p><strong>Type:</strong> {escalation.trigger_type}</p>
                  <p><strong>Priority:</strong> {escalation.severity_display}</p>
                  <p><strong>Status:</strong> {escalation.status_display}</p>
                  <p><strong>Created:</strong> {new Date(escalation.created_at).toLocaleString()}</p>
                </div>
              </div>

              {/* Description */}
              <div className="mb-6">
                <h3 className="font-semibold text-gray-900 mb-2">Complaint Description</h3>
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-gray-800">{escalation.description}</p>
                </div>
              </div>

              {/* Agent Assignment */}
              <div className="mb-6">
                <h3 className="font-semibold text-gray-900 mb-2">Agent Assignment</h3>
                <div className="flex gap-4 items-center">
                  <select 
                    value={selectedAgent} 
                    onChange={(e) => setSelectedAgent(e.target.value)}
                    className="border rounded px-3 py-2 flex-1"
                  >
                    <option value="">Select Agent...</option>
                    {agents.map(agent => (
                      <option key={agent.id} value={agent.id}>
                        {agent.name} ({agent.workload.capacity_remaining} capacity remaining)
                      </option>
                    ))}
                  </select>
                  <button 
                    onClick={handleAssignAgent}
                    disabled={!selectedAgent}
                    className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-300"
                  >
                    Assign
                  </button>
                </div>
              </div>

              {/* Contact Management */}
              <div className="mb-6">
                <h3 className="font-semibold text-gray-900 mb-2">Customer Contact</h3>
                <div className="bg-yellow-50 rounded-lg p-4 mb-4">
                  <p><strong>Contact Attempts:</strong> {escalation.contact_attempts}</p>
                  <p><strong>Should Contact:</strong> {escalation.should_contact ? '✅ Yes' : '❌ No'}</p>
                  {escalation.last_contact_attempt && (
                    <p><strong>Last Attempt:</strong> {new Date(escalation.last_contact_attempt).toLocaleString()}</p>
                  )}
                </div>

                <div className="flex gap-2 mb-4">
                  <button 
                    onClick={handleScheduleContact}
                    className="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600"
                  >
                    Schedule Contact
                  </button>
                </div>

                <div className="space-y-4">
                  <textarea
                    value={contactNotes}
                    onChange={(e) => setContactNotes(e.target.value)}
                    placeholder="Contact attempt notes..."
                    rows={3}
                    className="w-full border rounded px-3 py-2"
                  />
                  <div className="flex gap-2">
                    <button 
                      onClick={() => handleRecordContact(true)}
                      className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
                    >
                      Record Successful Contact
                    </button>
                    <button 
                      onClick={() => handleRecordContact(false)}
                      className="px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600"
                    >
                      Record Failed Contact
                    </button>
                  </div>
                </div>
              </div>

              {/* Resolution */}
              {escalation.resolution_status !== 'resolved' && (
                <div className="mb-6">
                  <h3 className="font-semibold text-gray-900 mb-2">Resolution</h3>
                  <textarea
                    value={resolutionNotes}
                    onChange={(e) => setResolutionNotes(e.target.value)}
                    placeholder="Resolution notes..."
                    rows={4}
                    className="w-full border rounded px-3 py-2 mb-4"
                  />
                  <button 
                    onClick={handleResolve}
                    className="px-6 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                  >
                    Mark as Resolved
                  </button>
                </div>
              )}

              {/* Conversation History */}
              {escalation.conversation_history && escalation.conversation_history.length > 0 && (
                <div className="mb-6">
                  <h3 className="font-semibold text-gray-900 mb-2">Recent WhatsApp Conversation</h3>
                  <div className="bg-gray-50 rounded-lg p-4 max-h-60 overflow-y-auto">
                    {escalation.conversation_history.map((msg, index) => (
                      <div key={index} className={`mb-2 ${msg.direction === 'incoming' ? 'text-blue-800' : 'text-green-800'}`}>
                        <div className="text-xs text-gray-500">
                          {new Date(msg.timestamp).toLocaleString()} - {msg.direction}
                        </div>
                        <div className="text-sm">{msg.content}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="p-8 text-center text-red-600">Error loading escalation details</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EscalationDetailModal;
```

### Vue.js Example

```vue
<template>
  <div class="escalations-dashboard">
    <!-- Statistics Cards -->
    <div class="stats-grid">
      <div class="stat-card">
        <h3>Total Escalations</h3>
        <p class="stat-number">{{ statistics.total }}</p>
      </div>
      <div class="stat-card">
        <h3>Pending</h3>
        <p class="stat-number pending">{{ statistics.pending }}</p>
      </div>
      <div class="stat-card">
        <h3>Urgent</h3>
        <p class="stat-number urgent">{{ statistics.urgent }}</p>
      </div>
      <div class="stat-card">
        <h3>Requires Contact</h3>
        <p class="stat-number contact">{{ statistics.requires_contact }}</p>
      </div>
    </div>

    <!-- Escalations List -->
    <div class="escalations-list">
      <div v-for="escalation in escalations" :key="escalation.id" class="escalation-card">
        <div class="escalation-header">
          <h4>{{ escalation.customer_name || 'Unknown Customer' }}</h4>
          <span :class="['priority-badge', escalation.severity_level]">
            {{ escalation.severity_display }}
          </span>
        </div>
        
        <div class="escalation-body">
          <p class="phone">📞 {{ escalation.customer_phone }}</p>
          <p class="description">{{ escalation.description }}</p>
          <p class="issue-type">{{ escalation.trigger_type }}</p>
        </div>

        <div class="escalation-actions">
          <button @click="viewDetails(escalation.id)" class="btn btn-primary">
            View Details
          </button>
          <a 
            v-if="escalation.should_contact"
            :href="`https://wa.me/${escalation.customer_phone.replace('+', '')}`"
            target="_blank"
            class="btn btn-whatsapp"
          >
            📱 WhatsApp
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'EscalationsDashboard',
  data() {
    return {
      escalations: [],
      statistics: {},
      loading: false
    };
  },
  async mounted() {
    await this.fetchEscalations();
  },
  methods: {
    async fetchEscalations() {
      try {
        this.loading = true;
        const response = await axios.get('/api/user/admin/support-escalations/');
        this.escalations = response.data.escalations;
        this.statistics = response.data.statistics;
      } catch (error) {
        console.error('Error fetching escalations:', error);
      } finally {
        this.loading = false;
      }
    },
    
    viewDetails(escalationId) {
      // Navigate to details page or open modal
      this.$router.push(`/admin/escalations/${escalationId}`);
    }
  }
};
</script>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.stat-number {
  font-size: 2rem;
  font-weight: bold;
  margin: 0;
}

.stat-number.pending { color: #f59e0b; }
.stat-number.urgent { color: #dc2626; }
.stat-number.contact { color: #7c3aed; }

.escalation-card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.priority-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
}

.priority-badge.urgent { background: #dc2626; color: white; }
.priority-badge.high { background: #ea580c; color: white; }
.priority-badge.medium { background: #ca8a04; color: white; }
.priority-badge.low { background: #16a34a; color: white; }

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  text-decoration: none;
  display: inline-block;
  margin-right: 0.5rem;
}

.btn-primary { background: #3b82f6; color: white; }
.btn-whatsapp { background: #25d366; color: white; }
</style>
```

## Authentication

All endpoints require authentication. Include the authorization header:

```javascript
// Using axios
const config = {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
};

axios.get('/api/user/admin/support-escalations/', config);
```

## WebSocket Integration (Optional)

For real-time notifications, you can integrate WebSocket connections:

```javascript
const ws = new WebSocket('ws://your-domain/ws/admin-notifications/');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  
  if (data.type === 'complaint_escalation') {
    // Show notification
    showNotification(`New ${data.severity} priority complaint from ${data.customer_phone}`);
    
    // Refresh escalations list
    fetchEscalations();
  }
};

function showNotification(message) {
  // Use your preferred notification library
  // e.g., react-toastify, vue-toasted, etc.
  alert(message);
}
```

## CSS Styling Guide

### Priority Colors
- 🚨 **Urgent**: `#dc2626` (Red 600)
- 🔴 **High**: `#ea580c` (Orange 600) 
- 🟡 **Medium**: `#ca8a04` (Yellow 600)
- 🟢 **Low**: `#16a34a` (Green 600)

### Status Colors
- **Pending**: `#6b7280` (Gray 500)
- **In Progress**: `#3b82f6` (Blue 500)
- **Contacted**: `#8b5cf6` (Purple 500)
- **Resolved**: `#16a34a` (Green 600)

## Error Handling

```javascript
const handleApiError = (error) => {
  if (error.response?.status === 401) {
    // Redirect to login
    window.location.href = '/login';
  } else if (error.response?.status === 403) {
    alert('You do not have permission to perform this action');
  } else {
    alert('An error occurred. Please try again.');
  }
  console.error('API Error:', error);
};
```

## Mobile Responsive Design

```css
/* Mobile-first responsive design */
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .escalation-actions {
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .escalation-actions .btn {
    width: 100%;
    text-align: center;
  }
}

@media (max-width: 480px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
```

This integration guide provides everything needed to implement the Support Escalation system in your admin dashboard, with complete examples for React and Vue.js, proper styling, and mobile responsiveness.