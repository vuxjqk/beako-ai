"use client";

import {
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  Lock,
  LockOpen,
  MoreHorizontal,
  Pencil,
  RotateCw,
  Search,
  UserPlus,
  Users,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";

import { FormAlert } from "@/components/form-alert";
import { EmptyState } from "@/components/page-shell";
import { UserAvatar } from "@/components/user-avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { adminUsersApi, PAGE_SIZES, type Page } from "@/lib/admin";
import { ROLE_LABELS, type User } from "@/lib/auth";
import { errorMessage } from "@/lib/errors";
import { cn } from "@/lib/utils";

import { ToggleActiveDialog } from "./toggle-active-dialog";
import { UserFormDialog } from "./user-form-dialog";

const SEARCH_DEBOUNCE_MS = 300;

const dateFormat = new Intl.DateTimeFormat("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });

type Query = { page: number; pageSize: number; search: string };
// Tagged with the query it answers, so "loading" is simply "the latest result is for another query"
type Result = { key: string } & ({ data: Page<User> } | { error: string });

export function UsersManager({ initial }: { initial: Query }) {
  const [query, setQuery] = useState<Query>(initial);
  const [searchInput, setSearchInput] = useState(initial.search);
  const [reloadToken, setReloadToken] = useState(0);
  const [result, setResult] = useState<Result | null>(null);

  const [formOpen, setFormOpen] = useState(false);
  const [formSession, setFormSession] = useState(0);
  const [editing, setEditing] = useState<User | undefined>();
  const [toggling, setToggling] = useState<User | null>(null);

  const key = JSON.stringify([query, reloadToken]);
  const loading = result?.key !== key;
  const data = result && "data" in result ? result.data : null;
  const loadError = result && "error" in result ? result.error : null;

  useEffect(() => {
    let cancelled = false;
    adminUsersApi
      .list(query)
      .then((page) => {
        if (cancelled) return;
        // Asked for a page past the end (e.g. a stale link): jump to the last one instead
        if (page.totalPages > 0 && query.page > page.totalPages) {
          setQuery((q) => ({ ...q, page: page.totalPages }));
          return;
        }
        setResult({ key, data: page });
      })
      .catch((error) => {
        if (!cancelled) setResult({ key, error: errorMessage(error) });
      });
    return () => {
      cancelled = true;
    };
    // `key` already encodes `query` and the reload token
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  // Keep the URL shareable and reload-safe without adding history entries
  useEffect(() => {
    const params = new URLSearchParams();
    if (query.page > 1) params.set("page", String(query.page));
    if (query.pageSize !== PAGE_SIZES[0]) params.set("pageSize", String(query.pageSize));
    if (query.search) params.set("search", query.search);
    const qs = params.toString();
    window.history.replaceState(null, "", qs ? `?${qs}` : window.location.pathname);
  }, [query]);

  // Debounce typing into the search box
  useEffect(() => {
    const search = searchInput.trim();
    if (search === query.search) return;
    const timer = setTimeout(() => setQuery((q) => ({ ...q, search, page: 1 })), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [searchInput, query.search]);

  const reload = () => setReloadToken((t) => t + 1);

  function replaceUser(updated: User) {
    setResult((r) =>
      r && "data" in r
        ? { ...r, data: { ...r.data, items: r.data.items.map((u) => (u.id === updated.id ? updated : u)) } }
        : r,
    );
  }

  function openForm(user?: User) {
    setEditing(user);
    setFormSession((s) => s + 1);
    setFormOpen(true);
  }

  function handleSaved(user: User, created: boolean) {
    setFormOpen(false);
    if (created) {
      // Newest accounts come first, so show page 1 without a filter that could hide it
      setSearchInput("");
      setQuery((q) => ({ ...q, search: "", page: 1 }));
      reload();
    } else {
      replaceUser(user);
    }
  }

  const items = data?.items ?? [];
  const firstRow = data && data.total > 0 ? (data.page - 1) * data.pageSize + 1 : 0;
  const lastRow = data ? (data.page - 1) * data.pageSize + data.items.length : 0;

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Tìm theo họ tên hoặc email"
            aria-label="Tìm kiếm người dùng"
            value={searchInput}
            maxLength={255}
            onChange={(event) => setSearchInput(event.target.value)}
            className="pr-8 pl-8 [&::-webkit-search-cancel-button]:hidden"
          />
          {searchInput && (
            <button
              type="button"
              onClick={() => setSearchInput("")}
              className="absolute inset-y-0 right-0 flex w-8 items-center justify-center text-muted-foreground hover:text-foreground"
              aria-label="Xoá tìm kiếm"
            >
              <X className="size-4" />
            </button>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="icon" onClick={reload} disabled={loading} aria-label="Tải lại">
            <RotateCw className={cn(loading && "animate-spin")} />
          </Button>
          <Button onClick={() => openForm()} className="flex-1 sm:flex-none">
            <UserPlus />
            Tạo tài khoản
          </Button>
        </div>
      </div>

      {loadError && !loading ? (
        <FormAlert variant="error" title="Không tải được danh sách">
          <p>{loadError}</p>
          <Button variant="outline" size="sm" className="mt-2" onClick={reload}>
            Thử lại
          </Button>
        </FormAlert>
      ) : !data ? (
        <ListSkeleton />
      ) : items.length === 0 ? (
        query.search ? (
          <EmptyState
            icon={Search}
            title="Không tìm thấy tài khoản"
            text={`Không có người dùng hay chuyên gia nào khớp với “${query.search}”.`}
          />
        ) : (
          <EmptyState
            icon={Users}
            title="Chưa có tài khoản nào"
            text="Người dùng và chuyên gia sẽ xuất hiện ở đây khi họ đăng ký hoặc khi bạn tạo tài khoản."
          />
        )
      ) : (
        <div className={cn("transition-opacity", loading && "pointer-events-none opacity-60")} aria-busy={loading}>
          {/* Desktop: table */}
          <div className="hidden rounded-xl border md:block">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="pl-4">Tài khoản</TableHead>
                  <TableHead>Vai trò</TableHead>
                  <TableHead>Trạng thái</TableHead>
                  <TableHead>Ngày tạo</TableHead>
                  <TableHead className="w-12 pr-4">
                    <span className="sr-only">Thao tác</span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell className="pl-4">
                      <UserIdentity user={user} />
                    </TableCell>
                    <TableCell>
                      <RoleBadge user={user} />
                    </TableCell>
                    <TableCell>
                      <StatusBadges user={user} />
                    </TableCell>
                    <TableCell className="text-muted-foreground">{dateFormat.format(new Date(user.createdAt))}</TableCell>
                    <TableCell className="pr-4 text-right">
                      <RowActions user={user} onEdit={openForm} onToggleActive={setToggling} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Mobile: cards */}
          <ul className="space-y-2 md:hidden">
            {items.map((user) => (
              <li key={user.id} className="rounded-xl border bg-card p-3">
                <div className="flex items-start gap-2">
                  <div className="min-w-0 flex-1">
                    <UserIdentity user={user} />
                  </div>
                  <RowActions user={user} onEdit={openForm} onToggleActive={setToggling} />
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-1.5 pl-11">
                  <RoleBadge user={user} />
                  <StatusBadges user={user} />
                  <span className="ml-auto text-xs text-muted-foreground">
                    {dateFormat.format(new Date(user.createdAt))}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {data && data.total > 0 && (
        <div className="flex flex-col-reverse items-center justify-between gap-3 text-sm text-muted-foreground sm:flex-row">
          <p>
            {firstRow}–{lastRow} trên {data.total} tài khoản
          </p>
          <div className="flex items-center gap-2">
            <Select
              value={String(query.pageSize)}
              onValueChange={(value) => setQuery((q) => ({ ...q, pageSize: Number(value), page: 1 }))}
            >
              <SelectTrigger size="sm" aria-label="Số dòng mỗi trang">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PAGE_SIZES.map((size) => (
                  <SelectItem key={size} value={String(size)}>
                    {size} / trang
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              variant="outline"
              size="icon-sm"
              aria-label="Trang trước"
              disabled={loading || query.page <= 1}
              onClick={() => setQuery((q) => ({ ...q, page: q.page - 1 }))}
            >
              <ChevronLeft />
            </Button>
            <span className="min-w-16 text-center tabular-nums">
              {data.page} / {data.totalPages}
            </span>
            <Button
              variant="outline"
              size="icon-sm"
              aria-label="Trang sau"
              disabled={loading || query.page >= data.totalPages}
              onClick={() => setQuery((q) => ({ ...q, page: q.page + 1 }))}
            >
              <ChevronRight />
            </Button>
          </div>
        </div>
      )}

      <UserFormDialog
        key={formSession}
        open={formOpen}
        onOpenChange={setFormOpen}
        user={editing}
        onSaved={handleSaved}
      />
      <ToggleActiveDialog
        user={toggling}
        onOpenChange={(open) => !open && setToggling(null)}
        onSaved={(user) => {
          setToggling(null);
          replaceUser(user);
        }}
      />
    </div>
  );
}

function UserIdentity({ user }: { user: User }) {
  return (
    <div className="flex min-w-0 items-center gap-3">
      <UserAvatar user={user} className={cn("size-8", !user.isActive && "opacity-50 grayscale")} />
      <div className="min-w-0">
        <p className="truncate font-medium">{user.fullName}</p>
        <p className="truncate text-xs text-muted-foreground">{user.email}</p>
      </div>
    </div>
  );
}

function RoleBadge({ user }: { user: User }) {
  return <Badge variant={user.role === "expert" ? "default" : "secondary"}>{ROLE_LABELS[user.role]}</Badge>;
}

function StatusBadges({ user }: { user: User }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {user.isActive ? (
        <Badge variant="outline" className="gap-1">
          <span className="size-1.5 rounded-full bg-emerald-500" />
          Hoạt động
        </Badge>
      ) : (
        <Badge variant="destructive" className="gap-1">
          <Lock />
          Đã khoá
        </Badge>
      )}
      {!user.emailVerifiedAt && (
        <Badge variant="secondary" className="gap-1">
          <CircleAlert className="text-amber-500" />
          Chưa xác thực
        </Badge>
      )}
      {user.googleLinked && <Badge variant="outline">Google</Badge>}
    </div>
  );
}

function RowActions({
  user,
  onEdit,
  onToggleActive,
}: {
  user: User;
  onEdit: (user: User) => void;
  onToggleActive: (user: User) => void;
}) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon-sm" aria-label={`Thao tác với ${user.fullName}`}>
          <MoreHorizontal />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onSelect={() => onEdit(user)}>
          <Pencil />
          Chỉnh sửa
        </DropdownMenuItem>
        {user.isActive ? (
          <DropdownMenuItem variant="destructive" onSelect={() => onToggleActive(user)}>
            <Lock />
            Khoá tài khoản
          </DropdownMenuItem>
        ) : (
          <DropdownMenuItem onSelect={() => onToggleActive(user)}>
            <LockOpen />
            Mở khoá
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function ListSkeleton() {
  return (
    <div className="space-y-2 rounded-xl border p-4" aria-busy="true" aria-label="Đang tải">
      {Array.from({ length: 5 }, (_, i) => (
        <div key={i} className="flex items-center gap-3 py-1.5">
          <Skeleton className="size-8 rounded-full" />
          <div className="flex-1 space-y-1.5">
            <Skeleton className="h-3.5 w-40" />
            <Skeleton className="h-3 w-56 max-w-full" />
          </div>
          <Skeleton className="hidden h-5 w-20 sm:block" />
        </div>
      ))}
    </div>
  );
}
