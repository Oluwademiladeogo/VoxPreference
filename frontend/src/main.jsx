import { StrictMode } from "react";
import "./index.css";
import LandingPage from "./pages/LandingPage.jsx";
import UploadPage from "./pages/UploadPage.jsx";
import TargetWordPage from "./pages/TargetWordPage.jsx";
import CriteriaPage from "./pages/CriteriaPage.jsx";
import ResultsPage from "./pages/ResultsPage.jsx";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import ReactDOM from "react-dom/client";

const root = document.getElementById("root");
ReactDOM.createRoot(root).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/target-word" element={<TargetWordPage />} />
        <Route path="/criteria" element={<CriteriaPage />} />
        <Route path="/results" element={<ResultsPage />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>
);
