import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8001";

export const api = axios.create({ baseURL: `${BACKEND_URL}/api` });

export const downloadUrl = (documentId) =>
  `${BACKEND_URL}/api/documents/${documentId}/download`;

export function errMessage(error) {
  return (
    error?.response?.data?.detail ||
    error?.message ||
    "Something went wrong — check that the backend is running."
  );
}
