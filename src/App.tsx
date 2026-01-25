import React from "react";
import { LandingPage } from "./pages/LandingPage";
import { DashboardPage } from "./pages/DashboardPage";
import { Toaster } from "sonner";
import { BrowserRouter, Routes, Route, Navigate, Link, useLocation } from "react-router-dom";
import { HomeIcon, ChartBarIcon } from "@heroicons/react/24/outline";

function Navigation() {
  const location = useLocation();
  
  return (
    <header className="sticky top-0 z-10 bg-white/90 backdrop-blur-md border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 h-16 flex justify-between items-center">
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-purple-600 rounded-xl flex items-center justify-center shadow-md group-hover:scale-105 transition-transform">
            <span className="text-white font-bold text-lg">MM</span>
          </div>
          <div>
            <h2 className="text-lg font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              MassMutual
            </h2>
            <p className="text-xs text-gray-500 font-medium">Data Pipeline</p>
          </div>
        </Link>

        <nav className="flex items-center gap-2">
          <Link
            to="/"
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-semibold transition-all ${
              location.pathname === "/"
                ? "bg-blue-100 text-blue-700"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            <HomeIcon className="w-5 h-5" />
            <span className="hidden md:inline">Home</span>
          </Link>
          <Link
            to="/dashboard"
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-semibold transition-all ${
              location.pathname === "/dashboard"
                ? "bg-purple-100 text-purple-700"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            <ChartBarIcon className="w-5 h-5" />
            <span className="hidden md:inline">Dashboard</span>
          </Link>
        </nav>
      </div>
    </header>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col bg-gradient-to-br from-gray-50 via-blue-50 to-purple-50">
        <Navigation />

        <main className="flex-1">
          <div className="max-w-7xl mx-auto px-4">
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
            </Routes>
          </div>
        </main>

        

        {/* <Toaster /> */}
      </div>
    </BrowserRouter>
  );
}
