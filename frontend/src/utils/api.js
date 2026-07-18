const API_BASE = "http://localhost:8000/api/v1";

const getHeaders = () => {
  const token = localStorage.getItem("token");
  const headers = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
};

export const api = {
  // Authentication services
  auth: {
    login: async (username, password) => {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Authentication failed");
      }
      const data = await response.json();
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("role", data.role);
      localStorage.setItem("username", data.username);
      return data;
    },
    logout: () => {
      localStorage.removeItem("token");
      localStorage.removeItem("role");
      localStorage.removeItem("username");
    },
    me: async () => {
      const res = await fetch(`${API_BASE}/auth/me`, { headers: getHeaders() });
      if (!res.ok) throw new Error("Could not fetch profile");
      return res.json();
    }
  },

  // Employees registry operations
  employees: {
    list: async (filters = {}) => {
      const params = new URLSearchParams();
      if (filters.username) params.append("username", filters.username);
      if (filters.employee_id) params.append("employee_id", filters.employee_id);
      if (filters.department) params.append("department", filters.department);
      if (filters.status) params.append("status", filters.status);
      
      const res = await fetch(`${API_BASE}/employees?${params.toString()}`, {
        headers: getHeaders()
      });
      if (!res.ok) throw new Error("Error loading employee logs directory");
      return res.json();
    },
    create: async (data) => {
      const res = await fetch(`${API_BASE}/employees`, {
        method: "POST",
        headers: getHeaders(),
        body: JSON.stringify(data)
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Error adding employee profile");
      }
      return res.json();
    },
    update: async (id, data) => {
      const res = await fetch(`${API_BASE}/employees/${id}`, {
        method: "PUT",
        headers: getHeaders(),
        body: JSON.stringify(data)
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Error modifying employee data");
      }
      return res.json();
    },
    delete: async (id) => {
      const res = await fetch(`${API_BASE}/employees/${id}`, {
        method: "DELETE",
        headers: getHeaders()
      });
      if (!res.ok) throw new Error("Could not delete employee profile");
    },
    getExcelUrl: (start, end, empId) => {
      let url = `${API_BASE}/employees/reports/excel?start_date=${start}&end_date=${end}`;
      if (empId) url += `&employee_id=${empId}`;
      return url;
    },
    getPdfUrl: (start, end, empId) => {
      let url = `${API_BASE}/employees/reports/pdf?start_date=${start}&end_date=${end}`;
      if (empId) url += `&employee_id=${empId}`;
      return url;
    }
  },

  // Cameras configurations operations
  cameras: {
    list: async () => {
      const res = await fetch(`${API_BASE}/cameras`, { headers: getHeaders() });
      if (!res.ok) throw new Error("Error loading cameras registry");
      return res.json();
    },
    create: async (data) => {
      const res = await fetch(`${API_BASE}/cameras`, {
        method: "POST",
        headers: getHeaders(),
        body: JSON.stringify(data)
      });
      if (!res.ok) throw new Error("Could not save camera profile");
      return res.json();
    },
    update: async (id, data) => {
      const res = await fetch(`${API_BASE}/cameras/${id}`, {
        method: "PUT",
        headers: getHeaders(),
        body: JSON.stringify(data)
      });
      if (!res.ok) throw new Error("Could not edit camera configs");
      return res.json();
    },
    delete: async (id) => {
      const res = await fetch(`${API_BASE}/cameras/${id}`, {
        method: "DELETE",
        headers: getHeaders()
      });
      if (!res.ok) throw new Error("Could not remove camera configuration");
    },
    getStreamUrl: (id) => {
      return `${API_BASE}/cameras/${id}/stream`;
    },
    getTelemetry: async (id) => {
      const res = await fetch(`${API_BASE}/cameras/${id}/telemetry`);
      if (!res.ok) throw new Error("Could not fetch telemetry data");
      return res.json();
    }
  },

  // Notifications settings & logs queries
  notifications: {
    getSettings: async () => {
      const res = await fetch(`${API_BASE}/notifications/settings`, { headers: getHeaders() });
      if (!res.ok) throw new Error("Error fetching settings configs");
      return res.json();
    },
    updateSettings: async (data) => {
      const res = await fetch(`${API_BASE}/notifications/settings`, {
        method: "PUT",
        headers: getHeaders(),
        body: JSON.stringify(data)
      });
      if (!res.ok) throw new Error("Error modifying notification settings");
      return res.json();
    },
    listAlerts: async () => {
      const res = await fetch(`${API_BASE}/notifications/logs`, { headers: getHeaders() });
      if (!res.ok) throw new Error("Error fetching notifications list");
      return res.json();
    }
  }
};
