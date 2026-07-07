import React from "react";
import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Agents from "./pages/Agents";
import Dashboard from "./pages/Dashboard";
import Forms from "./pages/Forms";
import Outbox from "./pages/Outbox";
import Patients from "./pages/Patients";
import Settings from "./pages/Settings";
import Templates from "./pages/Templates";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/patients" element={<Patients />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/forms" element={<Forms />} />
        <Route path="/templates" element={<Templates />} />
        <Route path="/outbox" element={<Outbox />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
