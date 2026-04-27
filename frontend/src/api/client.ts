// Get backend URL from current origin, just change the port if needed
const getBackendUrl = () => {
  const { hostname } = window.location;
  return `http://${hostname}:8000/api`;
};

const BASE_URL = getBackendUrl();

export interface ValidationError {
  field: string;
  message: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public errors?: ValidationError[],
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiRequest<T>(
  endpoint: string,
  method: string = "GET",
  body?: unknown,
): Promise<T> {
  const res = await fetch(`${BASE_URL}${endpoint}`, {
    method,
    headers: {
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({})) as {
      detail?: string;
      message?: string;
      errors?: ValidationError[];
    };

    const message = errorData.detail || errorData.message || "API Error";
    const errors = errorData.errors;

    throw new ApiError(message, res.status, errors);
  }

  return res.json() as Promise<T>;
}

// Multipart variant for PDF upload (with 5 minute timeout for processing)
export async function apiUpload<T>(endpoint: string, formData: FormData): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 5 * 60 * 1000); // 5 minutes

  try {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({})) as {
        detail?: string;
        message?: string;
        errors?: ValidationError[];
      };

      const message = errorData.detail || errorData.message || "Upload failed";
      const errors = errorData.errors;

      throw new ApiError(message, res.status, errors);
    }
    return res.json() as Promise<T>;
  } finally {
    clearTimeout(timeoutId);
  }
}
