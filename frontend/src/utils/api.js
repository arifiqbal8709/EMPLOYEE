const API_BASE = "http://localhost:8000/api/v1";

export const AUTH_SESSION_EXPIRED_EVENT = "auth:session-expired";

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

const notifySessionExpired = () => {
  localStorage.removeItem("token");
  localStorage.removeItem("role");
  localStorage.removeItem("username");
  window.dispatchEvent(new CustomEvent(AUTH_SESSION_EXPIRED_EVENT));
};

const handleResponse = async (res, defaultMsg = "Operation failed") => {
  if (!res.ok) {
    if (res.status === 401) {
      notifySessionExpired();
      throw new Error("Your session has expired. Please log in again.");
    }
    if (res.status === 403) {
      throw new Error("Permission denied. You do not have access to perform this action.");
    }
    let errData = {};
    try {
      errData = await res.json();
    } catch (e) {}
    throw new Error(errData.detail || `${defaultMsg} (Code: ${res.status})`);
  }
  if (res.status === 204) return null;
  return res.json();
};

const safeFetch = async (url, options = {}, defaultMsg = "Request failed", allowRefresh = true) => {
  try {
    const isLogin = url.includes("/auth/login");
    const token = localStorage.getItem("token");

    if (!token && !isLogin) {
      notifySessionExpired();
      throw new Error("Your session has expired. Please log in again.");
    }

    const mergedOptions = {
      ...options,
      headers: {
        ...getHeaders(),
        ...(options.headers || {}),
      },
    };

    const res = await fetch(url, mergedOptions);

    if (res.status === 401 && allowRefresh && token && !isLogin) {
      // Attempt token refresh seamlessly
      try {
        const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          headers: getHeaders(),
        });
        if (refreshRes.ok) {
          const refreshData = await refreshRes.json();
          localStorage.setItem("token", refreshData.access_token);
          localStorage.setItem("role", refreshData.role);
          localStorage.setItem("username", refreshData.username);

          // Retry original request with refreshed token
          const retryOptions = {
            ...options,
            headers: {
              ...getHeaders(),
              ...(options.headers || {}),
            },
          };
          const retriedRes = await fetch(url, retryOptions);
          return await handleResponse(retriedRes, defaultMsg);
        }
      } catch (refreshErr) {
        // Refresh failed, proceed to notify expiration
      }
    }

    return await handleResponse(res, defaultMsg);
  } catch (err) {
    if (err.name === "TypeError" && (err.message.includes("fetch") || err.message.includes("NetworkError") || err.message.includes("Failed to fetch"))) {
      throw new Error("Unable to connect to server. Please verify the backend service is active.");
    }
    throw err;
  }
};

export const api = {
  // Authentication services
  auth: {
    login: async (username, password) => {
      const data = await safeFetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      }, "Authentication failed. Please check your credentials.");

      if (data && data.access_token) {
        localStorage.setItem("token", data.access_token);
        localStorage.setItem("role", data.role || "employee");
        localStorage.setItem("username", data.username || username);
      }
      return data;
    },
    logout: () => {
      localStorage.removeItem("token");
      localStorage.removeItem("role");
      localStorage.removeItem("username");
    },
    me: async () => {
      return safeFetch(`${API_BASE}/auth/me`, { headers: getHeaders() }, "Could not retrieve user profile.");
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
      
      const data = await safeFetch(`${API_BASE}/employees?${params.toString()}`, {
        headers: getHeaders()
      }, "Unable to load employee directory.");
      return Array.isArray(data) ? data : [];
    },
    create: async (data) => {
      return safeFetch(`${API_BASE}/employees`, {
        method: "POST",
        headers: getHeaders(),
        body: JSON.stringify(data)
      }, "Could not register new employee profile.");
    },
    update: async (id, data) => {
      return safeFetch(`${API_BASE}/employees/${id}`, {
        method: "PUT",
        headers: getHeaders(),
        body: JSON.stringify(data)
      }, "Could not update employee details.");
    },
    delete: async (id) => {
      return safeFetch(`${API_BASE}/employees/${id}`, {
        method: "DELETE",
        headers: getHeaders()
      }, "Could not remove employee record.");
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
      const data = await safeFetch(`${API_BASE}/cameras`, { headers: getHeaders() }, "Unable to load camera configurations.");
      return Array.isArray(data) ? data : [];
    },
    create: async (data) => {
      return safeFetch(`${API_BASE}/cameras`, {
        method: "POST",
        headers: getHeaders(),
        body: JSON.stringify(data)
      }, "Could not add camera profile.");
    },
    update: async (id, data) => {
      return safeFetch(`${API_BASE}/cameras/${id}`, {
        method: "PUT",
        headers: getHeaders(),
        body: JSON.stringify(data)
      }, "Could not update camera settings.");
    },
    delete: async (id) => {
      return safeFetch(`${API_BASE}/cameras/${id}`, {
        method: "DELETE",
        headers: getHeaders()
      }, "Could not remove camera configuration.");
    },
    getStreamUrl: (id) => {
      return `${API_BASE}/cameras/${id}/stream`;
    },
    getTelemetry: async (id) => {
      return safeFetch(`${API_BASE}/cameras/${id}/telemetry`, {}, "Could not load camera telemetry.");
    },
    getTestingMode: async () => {
      return safeFetch(`${API_BASE}/cameras/testing-mode`, { headers: getHeaders() }, "Could not fetch testing mode status.");
    },
    setTestingMode: async (enabled) => {
      return safeFetch(`${API_BASE}/cameras/testing-mode`, {
        method: "POST",
        headers: getHeaders(),
        body: JSON.stringify({ enabled })
      }, "Could not update testing mode status.");
    }
  },

  // Notifications settings & logs queries
  notifications: {
    getSettings: async () => {
      return safeFetch(`${API_BASE}/notifications/settings`, { headers: getHeaders() }, "Unable to load notification settings.");
    },
    updateSettings: async (data) => {
      return safeFetch(`${API_BASE}/notifications/settings`, {
        method: "PUT",
        headers: getHeaders(),
        body: JSON.stringify(data)
      }, "Could not update notification settings.");
    },
    listAlerts: async () => {
      const data = await safeFetch(`${API_BASE}/notifications/logs`, { headers: getHeaders() }, "Unable to load notification alerts.");
      return Array.isArray(data) ? data : [];
    }
  }
};
