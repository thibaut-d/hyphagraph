import { Avatar } from "@mui/material";

interface UserAvatarProps {
  email: string;
  name?: string;
  size?: number;
}

/**
 * User avatar component that displays user initials on a colored background.
 * Falls back to first 2 letters of email if no name is provided.
 */
export function UserAvatar({ email, name, size = 40 }: UserAvatarProps) {
  // Get initials from name or email
  const getInitials = (): string => {
    if (name) {
      // If name is provided, use first letter of first and last name
      const parts = name.trim().split(/\s+/);
      if (parts.length >= 2) {
        return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
      }
      return parts[0].substring(0, 2).toUpperCase();
    }

    // Fall back to first 2 letters of email
    return email.substring(0, 2).toUpperCase();
  };

  // Generate a consistent color from the email
  const getBackgroundColor = (): string => {
    // Use email to generate a hash for consistent color
    let hash = 0;
    for (let i = 0; i < email.length; i++) {
      hash = email.charCodeAt(i) + ((hash << 5) - hash);
    }

    // Generate a pleasant color (avoid too dark or too light)
    const hue = Math.abs(hash % 360);
    const saturation = 65; // Medium saturation
    const lightness = 50; // Medium lightness

    return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
  };

  return (
    <Avatar
      sx={{
        width: size,
        height: size,
        bgcolor: getBackgroundColor(),
        fontSize: size * 0.4,
        fontWeight: 600,
        cursor: "pointer",
      }}
    >
      {getInitials()}
    </Avatar>
  );
}
