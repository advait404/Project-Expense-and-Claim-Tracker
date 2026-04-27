import { apiRequest } from "./client";
import type { Project, ProjectSummary } from "@/types";

// TODO: connect to backend endpoint: GET /api/projects/summary
export const getProjectsSummary = () =>
  apiRequest<ProjectSummary[]>("/projects/summary");

// TODO: connect to backend endpoint: GET /api/projects
export const getProjects = () => apiRequest<Project[]>("/projects");

// TODO: connect to backend endpoint: GET /api/projects/:id
export const getProject = (id: string) => apiRequest<Project>(`/projects/${id}`);

// TODO: connect to backend endpoint: POST /api/projects
export const createProject = (data: Partial<Project>) =>
  apiRequest<Project>("/projects", "POST", data);

// TODO: connect to backend endpoint: PUT /api/projects/:id
export const updateProject = (id: string, data: Partial<Project>) =>
  apiRequest<Project>(`/projects/${id}`, "PUT", data);

// TODO: connect to backend endpoint: DELETE /api/projects/:id
export const deleteProject = (id: string) =>
  apiRequest<void>(`/projects/${id}`, "DELETE");
