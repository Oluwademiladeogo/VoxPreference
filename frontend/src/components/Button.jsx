import React from "react";

const Button = ({
  onClick,
  children,
  disabled = false,
  loading = false,
  className = "",
  icon = null,
  position = "right", // 'left' or 'right'
}) => {
  const baseClasses =
    "w-32 h-12 flex items-center justify-center gap-2 rounded-full bg-purple-500 text-white font-medium text-base transition-all duration-300 shadow-sm hover:bg-purple-700 hover:scale-105 active:scale-95 focus:outline-none focus:ring-2 focus:ring-purple-300 hover:shadow-md";
  const disabledClasses =
    "opacity-50 cursor-not-allowed hover:scale-100 hover:shadow-sm";
  const positionClasses = position === "left" ? "self-start" : "self-end";

  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={`${baseClasses} ${
        disabled ? disabledClasses : ""
      } ${positionClasses} ${className}`}
    >
      {icon && (
        <span className="transform transition-transform duration-300 group-hover:-translate-x-1">
          {icon}
        </span>
      )}
      {loading ? "Loading..." : children}
    </button>
  );
};

export default Button;
