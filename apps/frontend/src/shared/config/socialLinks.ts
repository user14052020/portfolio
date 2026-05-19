export const contactSocialLinks = [
  {
    key: "telegram",
    label: "Telegram",
    placeholder: "https://t.me/username",
  },
  {
    key: "vk",
    label: "VK",
    placeholder: "https://vk.com/username",
  },
  {
    key: "youtube",
    label: "YouTube",
    placeholder: "https://youtube.com/@username",
  },
  {
    key: "rutube",
    label: "Rutube",
    placeholder: "https://rutube.ru/channel/00000000/",
  },
  {
    key: "dzen",
    label: "Dzen",
    placeholder: "https://dzen.ru/username",
  },
] as const;

export type ContactSocialKey = (typeof contactSocialLinks)[number]["key"];

export function resolveExternalUrl(value?: string | null): string {
  const url = value?.trim() ?? "";

  if (!url) {
    return "";
  }

  return /^https?:\/\//i.test(url) ? url : `https://${url}`;
}
