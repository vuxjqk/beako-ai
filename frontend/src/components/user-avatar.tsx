import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { avatarUrl, initials, type User } from "@/lib/auth";

export function UserAvatar({ user, className }: { user: Pick<User, "fullName" | "avatar">; className?: string }) {
  return (
    <Avatar className={className}>
      {/* Google profile pictures can refuse requests that carry a Referer */}
      <AvatarImage src={avatarUrl(user.avatar)} alt={user.fullName} referrerPolicy="no-referrer" />
      <AvatarFallback className="text-xs font-medium">{initials(user.fullName)}</AvatarFallback>
    </Avatar>
  );
}
