import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { DocumentViewerPage } from "@/pages/DocumentViewerPage";
import { HomePage } from "@/pages/HomePage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/documents/:documentId" element={<DocumentViewerPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
