"use client";

import { REGEXP_ONLY_DIGITS } from "input-otp";

import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp";

type OtpInputProps = {
  id?: string;
  value: string;
  onChange: (value: string) => void;
  onComplete?: (value: string) => void;
  disabled?: boolean;
  invalid?: boolean;
  autoFocus?: boolean;
};

/** 6-digit numeric code input used for email verification and password reset. */
export function OtpInput({ id, value, onChange, onComplete, disabled, invalid, autoFocus }: OtpInputProps) {
  return (
    <InputOTP
      id={id}
      maxLength={6}
      pattern={REGEXP_ONLY_DIGITS}
      inputMode="numeric"
      autoComplete="one-time-code"
      value={value}
      onChange={onChange}
      onComplete={onComplete}
      disabled={disabled}
      autoFocus={autoFocus}
      aria-invalid={invalid}
      containerClassName="justify-center"
    >
      <InputOTPGroup>
        {Array.from({ length: 6 }, (_, index) => (
          <InputOTPSlot key={index} index={index} aria-invalid={invalid} className="size-11 text-base" />
        ))}
      </InputOTPGroup>
    </InputOTP>
  );
}
