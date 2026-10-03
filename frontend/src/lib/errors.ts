import { ApiError, NetworkError, SessionExpiredError } from "@/lib/api";

export const NETWORK_ERROR_MESSAGE =
  "Không thể kết nối tới máy chủ. Vui lòng kiểm tra kết nối mạng và thử lại.";

/**
 * Turn any thrown error into a Vietnamese message for the user.
 * `byStatus` overrides the message for specific HTTP status codes.
 */
export function errorMessage(
  error: unknown,
  byStatus: Partial<Record<number, string>> = {},
): string {
  if (error instanceof NetworkError) return NETWORK_ERROR_MESSAGE;
  if (error instanceof SessionExpiredError) {
    return "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.";
  }
  if (error instanceof ApiError) {
    const override = byStatus[error.status];
    if (override) return override;
    if (error.status === 429) {
      return `Bạn thao tác quá nhanh. Vui lòng thử lại sau ${error.retryAfter ?? 60} giây.`;
    }
    if (error.status === 422) return "Dữ liệu không hợp lệ. Vui lòng kiểm tra lại.";
    if (error.status >= 500) return "Máy chủ đang gặp sự cố. Vui lòng thử lại sau ít phút.";
  }
  return "Đã có lỗi xảy ra. Vui lòng thử lại.";
}

export function isStatus(error: unknown, status: number): error is ApiError {
  return error instanceof ApiError && error.status === status;
}
