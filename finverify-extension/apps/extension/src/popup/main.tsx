import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Popup } from "@/popup/Popup";
import "@/popup/popup.css";

const container = document.getElementById("root");
if (!container) throw new Error("Popup root element not found");

createRoot(container).render(
  <StrictMode>
    <Popup />
  </StrictMode>,
);
