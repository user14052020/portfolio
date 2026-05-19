import type { ContactSocialKey } from "@/shared/config/socialLinks";

type BrandSocialIconProps = {
  socialKey: ContactSocialKey;
  className?: string;
};

export function BrandSocialIcon({ socialKey, className }: BrandSocialIconProps) {
  if (socialKey === "telegram") {
    return (
      <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
        <path
          d="M21.5 4.2 18.3 19c-.2 1-1 1.2-1.8.7l-5-3.7-2.4 2.3c-.3.3-.5.5-1 .5l.3-5.1 9.3-8.4c.4-.4-.1-.6-.6-.2L5.7 12.3.8 10.8c-1-.3-1-1 .2-1.5L20 2c.9-.3 1.7.2 1.4 2.2Z"
          fill="currentColor"
        />
      </svg>
    );
  }

  if (socialKey === "vk") {
    return (
      <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
        <path
          d="M3.1 7.7c.1 5.8 3 9.2 8.2 9.2h.3v-3.3c1.9.2 3.3 1.6 3.9 3.3h2.9c-.7-2.6-2.5-4.1-3.6-4.7 1.1-.8 2.7-2.6 3.1-4.5h-2.7c-.6 1.8-2.1 3.6-3.6 3.8V7.7H8.9v6.7c-1.7-.4-3.8-2.4-3.9-6.7H3.1Z"
          fill="currentColor"
        />
      </svg>
    );
  }

  if (socialKey === "youtube") {
    return (
      <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
        <path
          d="M21.6 7.3a3 3 0 0 0-2.1-2.1C17.7 4.7 12 4.7 12 4.7s-5.7 0-7.5.5a3 3 0 0 0-2.1 2.1A31 31 0 0 0 2 12a31 31 0 0 0 .4 4.7 3 3 0 0 0 2.1 2.1c1.8.5 7.5.5 7.5.5s5.7 0 7.5-.5a3 3 0 0 0 2.1-2.1c.4-1.8.4-4.7.4-4.7s0-2.9-.4-4.7Z"
          fill="currentColor"
        />
        <path
          d="m10.1 15.2 5-3.2-5-3.2v6.4Z"
          fill="currentColor"
          className="text-[#111318] transition group-hover:text-white"
        />
      </svg>
    );
  }

  if (socialKey === "rutube") {
    return (
      <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
        <path
          d="M4 5.5C4 4.7 4.7 4 5.5 4h13c.8 0 1.5.7 1.5 1.5v13c0 .8-.7 1.5-1.5 1.5h-13c-.8 0-1.5-.7-1.5-1.5v-13Z"
          fill="currentColor"
        />
        <path
          d="M8 8h5.7c1.8 0 3 1.1 3 2.8 0 1.2-.6 2.1-1.7 2.5l1.9 2.7h-2.8l-1.6-2.4h-2V16H8V8Zm2.5 2.1v1.5h2.8c.6 0 .9-.3.9-.8s-.3-.7-.9-.7h-2.8Z"
          fill="currentColor"
          className="text-[#111318] transition group-hover:text-white"
        />
      </svg>
    );
  }

  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M12 2.4c3.1 0 5.6 2.5 5.6 5.6 0 1.2-1 2.2-2.2 2.2H12V2.4Z" fill="currentColor" />
      <path d="M12 21.6A5.6 5.6 0 0 1 6.4 16c0-1.2 1-2.2 2.2-2.2H12v7.8Z" fill="currentColor" />
      <path d="M2.4 12c0-3.1 2.5-5.6 5.6-5.6 1.2 0 2.2 1 2.2 2.2V12H2.4Z" fill="currentColor" />
      <path d="M21.6 12c0 3.1-2.5 5.6-5.6 5.6-1.2 0-2.2-1-2.2-2.2V12h7.8Z" fill="currentColor" />
    </svg>
  );
}
