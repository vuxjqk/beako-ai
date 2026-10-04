"use client";

import { CircleAlert, CircleCheck, CirclePause, RotateCw, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";

import { FormAlert } from "@/components/form-alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { adminUsageApi, USAGE_RANGES, type UsageDay, type UsageReport } from "@/lib/admin";
import { errorMessage } from "@/lib/errors";
import { cn } from "@/lib/utils";

const usd = (n: number) => `$${n < 1 ? n.toFixed(4) : n.toFixed(2)}`;
const pct = (x: number | null) => (x === null ? "–" : `${Math.round(x * 100)}%`);
const int = new Intl.NumberFormat("vi-VN");
const seconds = (ms: number | null) => (ms === null ? "–" : `${(ms / 1000).toFixed(1)} s`);
const dayLabel = (iso: string) => {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
};

/** The day before a YYYY-MM-DD date. */
function previousDay(iso: string): string {
  const date = new Date(`${iso}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() - 1);
  return date.toISOString().slice(0, 10);
}

const STATE = {
  normal: { label: "Bình thường", icon: CircleCheck, variant: "secondary" },
  degraded: { label: "Đã tắt agent", icon: TriangleAlert, variant: "outline" },
  stopped: { label: "Tạm dừng", icon: CirclePause, variant: "destructive" },
} as const;

const ISSUE_LABELS: Record<string, string> = {
  input_rejected: "Câu hỏi bị chặn (prompt injection)",
  busy: "Đang có câu hỏi khác chạy",
  rate_limited: "Hỏi quá nhanh",
  user_quota: "Hết hạn mức ngày của người dùng",
  budget: "Hết ngân sách hệ thống",
  conversation_not_found: "Cuộc trò chuyện không tồn tại",
  client_disconnected: "Người dùng rời trang giữa chừng (đã dừng)",
  output_blocked: "Câu trả lời lộ prompt (đã thay)",
  quota: "Nhà cung cấp hết quota",
  rate_limited_llm: "Nhà cung cấp giới hạn tốc độ",
  unavailable: "Nhà cung cấp không khả dụng",
  timeout: "Nhà cung cấp quá thời gian",
  empty: "Nhà cung cấp trả rỗng",
  not_configured: "Chưa cấu hình / sai khóa API",
  internal: "Lỗi nội bộ",
};

function issueLabel(status: string, kind: string | null): string {
  if (!kind) return status === "error" ? "Lỗi không rõ" : "Không rõ";
  if (status === "error" && kind === "rate_limited") return ISSUE_LABELS.rate_limited_llm;
  return ISSUE_LABELS[kind] ?? kind;
}

type Result = { days: number } & ({ data: UsageReport } | { error: string });

export function UsageReportView() {
  const [days, setDays] = useState<number>(USAGE_RANGES[0]);
  const [reloadToken, setReloadToken] = useState(0);
  const [result, setResult] = useState<Result | null>(null);

  useEffect(() => {
    let cancelled = false;
    adminUsageApi
      .report(days)
      .then((data) => !cancelled && setResult({ days, data }))
      .catch((error) => !cancelled && setResult({ days, error: errorMessage(error) }));
    return () => {
      cancelled = true;
    };
  }, [days, reloadToken]);

  const data = result && "data" in result ? result.data : null;
  const loading = !result || result.days !== days;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2">
        <Select value={String(days)} onValueChange={(v) => setDays(Number(v))}>
          <SelectTrigger className="w-40" aria-label="Khoảng thời gian">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {USAGE_RANGES.map((n) => (
              <SelectItem key={n} value={String(n)}>
                {n} ngày gần nhất
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button variant="outline" size="icon" onClick={() => setReloadToken((t) => t + 1)} aria-label="Tải lại">
          <RotateCw className={cn(loading && "animate-spin")} />
        </Button>
        {data && <span className="text-xs text-muted-foreground">Ngày tính theo múi giờ {data.timezone}</span>}
      </div>

      {result && "error" in result && <FormAlert>{result.error}</FormAlert>}
      {!data && !(result && "error" in result) && <Skeleton className="h-96 w-full" />}
      {data && <Report report={data} />}
    </div>
  );
}

function Report({ report }: { report: UsageReport }) {
  const { today, limits } = report;
  const yesterdayIso = previousDay(today.date);
  const byDay = new Map(report.days.map((d) => [d.day, d]));
  const yesterday = byDay.get(yesterdayIso);
  const todayRow = byDay.get(today.date);
  const state = STATE[today.state];

  return (
    <>
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="gap-2">
          <CardHeader>
            <CardDescription>Chi phí hôm nay</CardDescription>
            <CardTitle className="text-2xl tabular-nums">{usd(today.spentUsd)}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            {today.budgetUsd !== null ? (
              <>
                <div className="h-1.5 overflow-hidden rounded-full bg-muted" aria-hidden>
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${Math.min(100, (today.spentUsd / today.budgetUsd) * 100)}%` }}
                  />
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span>trên ngân sách {usd(today.budgetUsd)}</span>
                  <Badge variant={state.variant}>
                    <state.icon />
                    {state.label}
                  </Badge>
                </div>
              </>
            ) : (
              <span>Không đặt trần chi phí</span>
            )}
            <p>{todayRow ? `${todayRow.questions} câu hỏi` : "Chưa có câu hỏi"}</p>
          </CardContent>
        </Card>

        <Stat
          label="Hôm qua: câu hỏi"
          value={yesterday ? int.format(yesterday.questions) : "0"}
          note={yesterday ? `${yesterday.users} người dùng · ${yesterday.rejected} bị từ chối` : "Không có dữ liệu"}
        />
        <Stat
          label="Hôm qua: chi phí"
          value={usd(yesterday?.costUsd ?? 0)}
          note={
            yesterday?.costPerQuestionUsd != null
              ? `${usd(yesterday.costPerQuestionUsd)}/câu · ${int.format(yesterday.promptTokens + yesterday.completionTokens)} token`
              : "Không có dữ liệu"
          }
        />
        <Stat
          label="Hôm qua: chất lượng"
          value={yesterday ? `${pct(yesterday.notFoundRate)} không tìm thấy` : "–"}
          note={
            yesterday
              ? `👎 ${pct(yesterday.thumbsDownRate)} (${yesterday.thumbsDown}/${yesterday.thumbsUp + yesterday.thumbsDown} đánh giá) · lỗi ${pct(yesterday.errorRate)}`
              : "Không có dữ liệu"
          }
        />
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Theo ngày</CardTitle>
          <CardDescription>
            “Không tìm thấy” tính trên câu đã trả lời; 👎 tính trên câu được đánh giá. Chi phí ước tính theo giá{" "}
            {limits.model}: ${limits.priceInputPerMtok}/${limits.priceOutputPerMtok} mỗi triệu token vào/ra.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {report.days.length === 0 ? (
            <p className="text-sm text-muted-foreground">Chưa có câu hỏi nào trong khoảng này.</p>
          ) : (
            <DaysTable days={report.days} />
          )}
        </CardContent>
      </Card>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Từ chối & lỗi</CardTitle>
            <CardDescription>Trong khoảng đã chọn</CardDescription>
          </CardHeader>
          <CardContent>
            {report.issues.length === 0 ? (
              <p className="flex items-center gap-2 text-sm text-muted-foreground">
                <CircleCheck className="size-4" /> Không có
              </p>
            ) : (
              <ul className="space-y-2 text-sm">
                {report.issues.map((i) => (
                  <li key={`${i.status}-${i.kind}`} className="flex items-center justify-between gap-3">
                    <span className="flex items-center gap-2">
                      {i.status === "error" ? (
                        <CircleAlert className="size-4 text-destructive" />
                      ) : (
                        <TriangleAlert className="size-4 text-muted-foreground" />
                      )}
                      {issueLabel(i.status, i.kind)}
                    </span>
                    <span className="tabular-nums text-muted-foreground">{i.count}</span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Người dùng tốn nhiều nhất hôm nay</CardTitle>
            <CardDescription>
              Hạn mức mỗi người: {limits.userPerMinute} câu/phút, {limits.userPerDay} câu/ngày,{" "}
              {int.format(limits.userDailyTokens)} token/ngày (quản trị viên được miễn)
            </CardDescription>
          </CardHeader>
          <CardContent>
            {report.topUsersToday.length === 0 ? (
              <p className="text-sm text-muted-foreground">Chưa có câu hỏi nào hôm nay.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Người dùng</TableHead>
                    <TableHead className="text-right">Câu hỏi</TableHead>
                    <TableHead className="text-right">Token</TableHead>
                    <TableHead className="text-right">Chi phí</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.topUsersToday.map((u) => (
                    <TableRow key={u.userId ?? "deleted"}>
                      <TableCell className="max-w-48 truncate">{u.email ?? "(tài khoản đã xóa)"}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {u.questions}
                        {u.rejected > 0 && <span className="text-muted-foreground"> (+{u.rejected} từ chối)</span>}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{int.format(u.tokens)}</TableCell>
                      <TableCell className="text-right tabular-nums">{usd(u.costUsd)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </section>
    </>
  );
}

function Stat({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <Card className="gap-2">
      <CardHeader>
        <CardDescription>{label}</CardDescription>
        <CardTitle className="text-2xl tabular-nums">{value}</CardTitle>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">{note}</CardContent>
    </Card>
  );
}

function DaysTable({ days }: { days: UsageDay[] }) {
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Ngày</TableHead>
            <TableHead className="text-right">Câu hỏi</TableHead>
            <TableHead className="text-right">Người dùng</TableHead>
            <TableHead className="text-right">Chi phí</TableHead>
            <TableHead className="text-right">Token vào / ra</TableHead>
            <TableHead className="text-right">Agent</TableHead>
            <TableHead className="text-right">Không tìm thấy</TableHead>
            <TableHead className="text-right">👍 / 👎</TableHead>
            <TableHead className="text-right">Tỉ lệ 👎</TableHead>
            <TableHead className="text-right">Lỗi</TableHead>
            <TableHead className="text-right">Từ chối</TableHead>
            <TableHead className="text-right">Độ trễ TB / p95</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {days.map((d) => (
            <TableRow key={d.day}>
              <TableCell className="font-medium">{dayLabel(d.day)}</TableCell>
              <TableCell className="text-right tabular-nums">{d.questions}</TableCell>
              <TableCell className="text-right tabular-nums">{d.users}</TableCell>
              <TableCell className="text-right tabular-nums">{usd(d.costUsd)}</TableCell>
              <TableCell className="text-right tabular-nums">
                {int.format(d.promptTokens)} / {int.format(d.completionTokens)}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {d.agent}
                {d.degraded > 0 && <span className="text-muted-foreground"> ({d.degraded} bị tắt)</span>}
              </TableCell>
              <TableCell className="text-right tabular-nums">{pct(d.notFoundRate)}</TableCell>
              <TableCell className="text-right tabular-nums">
                {d.thumbsUp} / {d.thumbsDown}
              </TableCell>
              <TableCell className="text-right tabular-nums">{pct(d.thumbsDownRate)}</TableCell>
              <TableCell className="text-right tabular-nums">{d.errors}</TableCell>
              <TableCell className="text-right tabular-nums">{d.rejected}</TableCell>
              <TableCell className="text-right tabular-nums">
                {seconds(d.latencyAvgMs)} / {seconds(d.latencyP95Ms)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
