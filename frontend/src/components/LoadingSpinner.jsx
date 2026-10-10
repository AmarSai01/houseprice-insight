const LoadingSpinner = ({ size = 'md' }) => {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12'
  }

  return (
    <div className="flex justify-center items-center" role="status" aria-label="Loading">
      <div
        className={`animate-spin rounded-full border-2 border-transparent border-b-[var(--hpi-color-on-accent,#f7f6f2)] ${sizeClasses[size]}`}
        aria-hidden="true"
      ></div>
    </div>
  )
}

export default LoadingSpinner
