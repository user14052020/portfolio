"use client";

/* eslint-disable @next/next/no-img-element -- Phone video posters are admin-managed media URLs. */

import type { MouseEvent } from "react";
import { useEffect, useRef, useState } from "react";
import {
  IconCalendar,
  IconChartLine,
  IconChevronDown,
  IconLayoutDashboard,
  IconMaximize,
  IconMinimize,
  IconPlayerPauseFilled,
  IconPlayerPlayFilled,
  IconSettings,
  IconShoppingBag,
  IconUsers,
  IconVolume,
  IconVolumeOff,
} from "@tabler/icons-react";

import { cn } from "@/shared/lib/cn";

type ShowcaseVideoFrameProps = {
  variant: string;
  duration: string;
  title: string;
  mediaUrl?: string | null;
  coverImage?: string | null;
  className?: string;
  onPlaybackStateChange?: (isPlaying: boolean) => void;
};

type VideoFitMode = "cover" | "contain";

const centerPlayButtonClassName =
  "absolute left-1/2 top-1/2 z-20 grid h-16 w-16 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full bg-black/45 text-white shadow-[0_18px_50px_rgba(0,0,0,0.24)] ring-1 ring-white/20 backdrop-blur-sm transition duration-200 hover:scale-105 hover:bg-black/60";
const videoControlButtonClassName =
  "grid h-8 w-8 place-items-center rounded-md bg-black/35 text-white ring-1 ring-white/10 backdrop-blur-sm transition hover:bg-black/55";

type FullscreenDocument = Document & {
  webkitFullscreenElement?: Element | null;
  webkitExitFullscreen?: () => Promise<void> | void;
};

type FullscreenElement = HTMLDivElement & {
  webkitRequestFullscreen?: () => Promise<void> | void;
};

type FullscreenVideoElement = HTMLVideoElement & {
  webkitDisplayingFullscreen?: boolean;
  webkitEnterFullscreen?: () => void;
  webkitExitFullscreen?: () => void;
};

export function ShowcaseVideoFrame({
  variant,
  duration,
  title,
  mediaUrl,
  coverImage,
  className,
  onPlaybackStateChange,
}: ShowcaseVideoFrameProps) {
  const normalizedVariant = variant || "dashboard-light";
  const shouldUseUploadedMedia = normalizedVariant === "uploaded-media" && (mediaUrl || coverImage);
  const visualVariant = shouldUseUploadedMedia ? "uploaded-media" : normalizedVariant;
  const hasPlayableVideo = visualVariant === "uploaded-media" && Boolean(mediaUrl);

  return (
    <div
      className={cn(
        "group relative isolate overflow-hidden rounded-lg border border-black/10 bg-[#0d0f14] shadow-[0_24px_70px_rgba(15,23,42,0.16)]",
        className,
      )}
    >
      <div className="aspect-[16/9] w-full overflow-hidden sm:min-h-[250px]">
        {visualVariant === "uploaded-media" ? (
          <UploadedMedia
            mediaUrl={mediaUrl}
            coverImage={coverImage}
            title={title}
            duration={duration}
            onPlaybackStateChange={onPlaybackStateChange}
          />
        ) : visualVariant === "chair-3d" ? (
          <ChairConfiguratorScene />
        ) : visualVariant === "finance-motion" ? (
          <FinanceMotionScene />
        ) : (
          <DashboardScene tone={visualVariant === "dashboard-dark" ? "dark" : "light"} />
        )}
      </div>

      {hasPlayableVideo ? null : (
        <button
          type="button"
          aria-label={`Play ${title}`}
          className={centerPlayButtonClassName}
        >
          <IconPlayerPlayFilled className="ml-1 h-8 w-8" aria-hidden />
        </button>
      )}

      {hasPlayableVideo ? null : <VideoControls duration={duration} />}
    </div>
  );
}

export function MobileVideoFrame({
  duration,
  title,
  mediaUrl,
  coverImage,
  className,
  onPlaybackStateChange,
}: Omit<ShowcaseVideoFrameProps, "variant">) {
  const hasPlayableVideo = Boolean(mediaUrl);

  return (
    <div className={cn("flex justify-center", className)}>
      <div className="relative w-full max-w-[290px] rounded-[2.35rem] border border-white/20 bg-[#111318] p-2.5 shadow-[0_28px_80px_rgba(15,23,42,0.28)] ring-1 ring-black/15 sm:max-w-[310px]">
        <div className="pointer-events-none absolute left-1/2 top-3 z-20 h-1.5 w-20 -translate-x-1/2 rounded-full bg-white/20" />
        <div className="relative overflow-hidden rounded-[1.8rem] bg-[#080a0f]">
          <div className="aspect-[332/720] w-full">
            {hasPlayableVideo ? (
              <UploadedVideoPlayer
                mediaUrl={mediaUrl as string}
                coverImage={coverImage}
                title={title}
                fallbackDuration={duration}
                fitMode="contain"
                posterFitMode="cover"
                onPlaybackStateChange={onPlaybackStateChange}
              />
            ) : coverImage ? (
              <img src={coverImage} alt="" className="h-full w-full object-cover" aria-hidden />
            ) : (
              <div className="grid h-full place-items-center px-8 text-center text-sm font-medium text-white/70">
                {title}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function UploadedMedia({
  mediaUrl,
  coverImage,
  title,
  duration,
  onPlaybackStateChange,
}: {
  mediaUrl?: string | null;
  coverImage?: string | null;
  title: string;
  duration: string;
  onPlaybackStateChange?: (isPlaying: boolean) => void;
}) {
  if (mediaUrl) {
    return (
      <UploadedVideoPlayer
        mediaUrl={mediaUrl}
        coverImage={coverImage}
        title={title}
        fallbackDuration={duration}
        onPlaybackStateChange={onPlaybackStateChange}
      />
    );
  }

  if (coverImage) {
    return <div className="h-full w-full bg-cover bg-center" style={{ backgroundImage: `url(${coverImage})` }} />;
  }

  return (
    <div className="grid h-full place-items-center bg-[#111318] px-8 text-center text-sm font-medium text-white/70">
      {title}
    </div>
  );
}

function UploadedVideoPlayer({
  mediaUrl,
  coverImage,
  title,
  fallbackDuration,
  videoClassName,
  fitMode = "cover",
  posterFitMode = "cover",
  onPlaybackStateChange,
}: {
  mediaUrl: string;
  coverImage?: string | null;
  title: string;
  fallbackDuration: string;
  videoClassName?: string;
  fitMode?: VideoFitMode;
  posterFitMode?: VideoFitMode;
  onPlaybackStateChange?: (isPlaying: boolean) => void;
}) {
  const frameRef = useRef<HTMLDivElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [durationSeconds, setDurationSeconds] = useState(0);

  useEffect(() => {
    const currentVideo = videoRef.current;
    if (!currentVideo) {
      return;
    }
    const videoElement: HTMLVideoElement = currentVideo;

    function syncTime() {
      setCurrentTime(videoElement.currentTime);
      if (Number.isFinite(videoElement.duration)) {
        setDurationSeconds(videoElement.duration);
      }
    }

    function syncPlaying() {
      const nextIsPlaying = !videoElement.paused && !videoElement.ended;
      setIsPlaying(nextIsPlaying);
      onPlaybackStateChange?.(nextIsPlaying);
    }

    videoElement.addEventListener("timeupdate", syncTime);
    videoElement.addEventListener("loadedmetadata", syncTime);
    videoElement.addEventListener("play", syncPlaying);
    videoElement.addEventListener("pause", syncPlaying);
    videoElement.addEventListener("ended", syncPlaying);

    return () => {
      videoElement.removeEventListener("timeupdate", syncTime);
      videoElement.removeEventListener("loadedmetadata", syncTime);
      videoElement.removeEventListener("play", syncPlaying);
      videoElement.removeEventListener("pause", syncPlaying);
      videoElement.removeEventListener("ended", syncPlaying);
    };
  }, [onPlaybackStateChange]);

  useEffect(() => {
    return () => {
      onPlaybackStateChange?.(false);
    };
  }, [onPlaybackStateChange]);

  useEffect(() => {
    const currentVideo = videoRef.current as FullscreenVideoElement | null;

    function syncFullscreenState() {
      const fullscreenDocument = document as FullscreenDocument;
      setIsFullscreen(
        Boolean(
          document.fullscreenElement ||
            fullscreenDocument.webkitFullscreenElement ||
            currentVideo?.webkitDisplayingFullscreen,
        ),
      );
    }

    document.addEventListener("fullscreenchange", syncFullscreenState);
    document.addEventListener("webkitfullscreenchange", syncFullscreenState);
    currentVideo?.addEventListener("webkitbeginfullscreen", syncFullscreenState);
    currentVideo?.addEventListener("webkitendfullscreen", syncFullscreenState);
    syncFullscreenState();

    return () => {
      document.removeEventListener("fullscreenchange", syncFullscreenState);
      document.removeEventListener("webkitfullscreenchange", syncFullscreenState);
      currentVideo?.removeEventListener("webkitbeginfullscreen", syncFullscreenState);
      currentVideo?.removeEventListener("webkitendfullscreen", syncFullscreenState);
    };
  }, []);

  async function togglePlayback() {
    const video = videoRef.current;
    if (!video) {
      return;
    }

    if (video.paused) {
      await video.play();
      return;
    }

    video.pause();
  }

  function toggleMuted() {
    const video = videoRef.current;
    if (!video) {
      return;
    }

    video.muted = !video.muted;
    setIsMuted(video.muted);
  }

  function seek(event: MouseEvent<HTMLButtonElement>) {
    const video = videoRef.current;
    const duration = durationSeconds || video?.duration;
    if (!video || !duration || !Number.isFinite(duration)) {
      return;
    }

    const rect = event.currentTarget.getBoundingClientRect();
    const ratio = Math.min(Math.max((event.clientX - rect.left) / rect.width, 0), 1);
    video.currentTime = ratio * duration;
    setCurrentTime(video.currentTime);
  }

  async function toggleFullscreen() {
    const target = frameRef.current as FullscreenElement | null;
    const video = videoRef.current as FullscreenVideoElement | null;
    const fullscreenDocument = document as FullscreenDocument;
    const hasStandardFullscreen = Boolean(document.fullscreenElement);
    const hasWebkitFullscreen = Boolean(fullscreenDocument.webkitFullscreenElement);
    const hasNativeVideoFullscreen = Boolean(video?.webkitDisplayingFullscreen);

    if (hasStandardFullscreen || hasWebkitFullscreen || hasNativeVideoFullscreen) {
      if (hasStandardFullscreen && document.exitFullscreen) {
        await document.exitFullscreen();
        return;
      }

      if (hasWebkitFullscreen && fullscreenDocument.webkitExitFullscreen) {
        await fullscreenDocument.webkitExitFullscreen();
        return;
      }

      if (hasNativeVideoFullscreen && video?.webkitExitFullscreen) {
        video.webkitExitFullscreen();
      }

      return;
    }

    if (target?.requestFullscreen) {
      try {
        await target.requestFullscreen();
        return;
      } catch {
        // iOS Safari exposes fullscreen only on the video element.
      }
    }

    if (target?.webkitRequestFullscreen) {
      try {
        await target.webkitRequestFullscreen();
        return;
      } catch {
        // Fall back to native media fullscreen below.
      }
    }

    video?.webkitEnterFullscreen?.();
  }

  const progress = durationSeconds > 0 ? Math.min((currentTime / durationSeconds) * 100, 100) : 0;
  const timelineLabel = `${formatVideoTime(currentTime)} / ${
    durationSeconds > 0 ? formatVideoTime(durationSeconds) : fallbackDuration
  }`;

  return (
    <div ref={frameRef} className="group/video relative flex h-full w-full items-center justify-center overflow-hidden bg-[#080a0f]">
      <video
        ref={videoRef}
        className={cn(
          "h-full w-full object-center",
          fitMode === "contain" ? "object-contain" : "object-cover",
          videoClassName,
        )}
        src={mediaUrl}
        poster={coverImage ?? undefined}
        preload="metadata"
        playsInline
      />

      {!isPlaying && currentTime <= 0.05 && coverImage ? (
        <img
          src={coverImage}
          alt=""
          className={cn(
            "pointer-events-none absolute inset-0 z-10 h-full w-full object-center",
            posterFitMode === "contain" ? "object-contain" : "object-cover",
          )}
          aria-hidden
        />
      ) : null}

      {!isPlaying ? (
        <button
          type="button"
          aria-label={`Play ${title}`}
          onClick={() => void togglePlayback()}
          className={centerPlayButtonClassName}
        >
          <IconPlayerPlayFilled className="ml-1 h-8 w-8" aria-hidden />
        </button>
      ) : null}

      <div className="absolute inset-x-3 bottom-3 z-30 rounded-lg bg-black/35 px-2.5 py-2 text-white shadow-[0_14px_42px_rgba(0,0,0,0.26)] ring-1 ring-white/10 backdrop-blur-sm sm:inset-x-4">
        <div className="mb-2 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button
              type="button"
              aria-label={isPlaying ? "Pause video" : "Play video"}
              onClick={() => void togglePlayback()}
              className={videoControlButtonClassName}
            >
              {isPlaying ? (
                <IconPlayerPauseFilled className="h-4 w-4" aria-hidden />
              ) : (
                <IconPlayerPlayFilled className="h-4 w-4" aria-hidden />
              )}
            </button>
            <span className="text-sm font-medium">{timelineLabel}</span>
          </div>
          <div className="flex items-center gap-5">
            <button
              type="button"
              aria-label={isMuted ? "Unmute video" : "Mute video"}
              onClick={toggleMuted}
              className={videoControlButtonClassName}
            >
              {isMuted ? <IconVolumeOff className="h-5 w-5" aria-hidden /> : <IconVolume className="h-5 w-5" aria-hidden />}
            </button>
            <button
              type="button"
              aria-label={isFullscreen ? "Exit fullscreen" : "Open fullscreen"}
              onClick={() => void toggleFullscreen()}
              className={videoControlButtonClassName}
            >
              {isFullscreen ? (
                <IconMinimize className="h-5 w-5" aria-hidden />
              ) : (
                <IconMaximize className="h-5 w-5" aria-hidden />
              )}
            </button>
          </div>
        </div>
        <button
          type="button"
          aria-label="Seek video"
          onClick={seek}
          className="block h-1 w-full overflow-hidden rounded-full bg-white/20 text-left"
        >
          <span className="block h-full rounded-full bg-white" style={{ width: `${progress}%` }} />
        </button>
      </div>
    </div>
  );
}

function formatVideoTime(value: number) {
  if (!Number.isFinite(value) || value <= 0) {
    return "0:00";
  }

  const minutes = Math.floor(value / 60);
  const seconds = Math.floor(value % 60);
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function VideoControls({ duration }: { duration: string }) {
  return (
    <div className="absolute inset-x-3 bottom-3 z-30 rounded-lg bg-black/35 px-2.5 py-2 text-white shadow-[0_14px_42px_rgba(0,0,0,0.26)] ring-1 ring-white/10 backdrop-blur-sm sm:inset-x-4">
      <div className="mb-2 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className={videoControlButtonClassName}>
            <IconPlayerPlayFilled className="h-4 w-4" aria-hidden />
          </span>
          <span className="text-sm font-medium">0:00 / {duration}</span>
        </div>
        <div className="flex items-center gap-5">
          <span className={videoControlButtonClassName}>
            <IconVolume className="h-5 w-5" aria-hidden />
          </span>
          <span className={videoControlButtonClassName}>
            <IconMaximize className="h-5 w-5" aria-hidden />
          </span>
        </div>
      </div>
      <div className="h-1 overflow-hidden rounded-full bg-white/20">
        <div className="h-full w-[32%] rounded-full bg-white" />
      </div>
    </div>
  );
}

function DashboardScene({ tone }: { tone: "dark" | "light" }) {
  const isDark = tone === "dark";
  const shellClass = isDark
    ? "bg-[radial-gradient(circle_at_78%_12%,rgba(70,91,135,0.25),transparent_18rem),linear-gradient(135deg,#11151d,#080a0f)] text-white"
    : "bg-[linear-gradient(180deg,#ffffff,#eef0f4)] text-[#111318]";
  const panelClass = isDark ? "border-white/10 bg-white/[0.045]" : "border-black/10 bg-white/80";
  const mutedClass = isDark ? "text-white/50" : "text-black/50";
  const lineClass = isDark ? "border-white/10" : "border-black/10";

  return (
    <div className={cn("relative h-full w-full p-5", shellClass)}>
      <div className="grid h-[calc(100%-58px)] grid-cols-[120px_1fr] overflow-hidden rounded-md border border-black/5 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]">
        <aside className={cn("space-y-4 border-r p-5 text-[11px]", lineClass)}>
          {[
            { Icon: IconLayoutDashboard, label: "Dashboard" },
            { Icon: IconChartLine, label: "Analytics" },
            { Icon: IconUsers, label: "Users" },
            { Icon: IconShoppingBag, label: "Products" },
            { Icon: IconSettings, label: "Settings" },
          ].map(({ Icon, label }, index) => (
            <div
              key={label}
              className={cn(
                "flex items-center gap-2 rounded-md px-2 py-2",
                index === 1 && (isDark ? "bg-white/10 text-white" : "bg-[#edf1fb] text-[#335cbd]"),
              )}
            >
              <Icon className="h-3.5 w-3.5" aria-hidden />
              <span>{label}</span>
            </div>
          ))}
        </aside>

        <div className="min-w-0 p-5">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-base font-semibold tracking-normal">Analytics overview</h3>
            <div className={cn("flex items-center gap-2 rounded-md border px-3 py-2 text-[11px]", panelClass)}>
              <IconCalendar className="h-3.5 w-3.5" aria-hidden />
              <span>May 12 - May 18</span>
              <IconChevronDown className="h-3.5 w-3.5" aria-hidden />
            </div>
          </div>

          <div className="grid grid-cols-5 gap-3">
            {[
              ["Total sales", "$98,540", "+14.2%"],
              ["Orders", "1,245", "+8.6%"],
              ["Customers", "8,320", "+12.1%"],
              ["Conversion rate", "2.34%", "+3.4%"],
              ["Revenue", "$12,430", "+15.1%"],
            ].map(([label, value, trend]) => (
              <div key={label} className={cn("rounded-md border p-4", panelClass)}>
                <p className={cn("text-[11px]", mutedClass)}>{label}</p>
                <div className="mt-3 flex items-end justify-between gap-2">
                  <p className="text-lg font-semibold tracking-normal">{value}</p>
                  <p className="text-[10px] text-[#5f7fe6]">{trend}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-4 grid grid-cols-[1.35fr_0.9fr] gap-4">
            <div className={cn("rounded-md border p-4", panelClass)}>
              <p className="mb-3 text-sm font-semibold">Sales</p>
              <div className="relative h-32 overflow-hidden">
                <div className={cn("absolute inset-0 bg-[linear-gradient(rgba(115,130,160,0.16)_1px,transparent_1px),linear-gradient(90deg,rgba(115,130,160,0.16)_1px,transparent_1px)] bg-[length:44px_28px]", isDark ? "opacity-35" : "opacity-55")} />
                <svg className="absolute inset-0 h-full w-full" viewBox="0 0 420 150" preserveAspectRatio="none">
                  <polyline
                    points="0,124 38,90 70,106 104,82 138,98 174,48 212,92 244,70 276,84 308,44 342,62 378,28 420,12"
                    fill="none"
                    stroke="#6687ec"
                    strokeWidth="3"
                  />
                </svg>
                <div className={cn("absolute bottom-0 flex w-full justify-between text-[10px]", mutedClass)}>
                  {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((item) => (
                    <span key={item}>{item}</span>
                  ))}
                </div>
              </div>
            </div>

            <div className={cn("rounded-md border p-4", panelClass)}>
              <p className="mb-4 text-sm font-semibold">Top products</p>
              <div className="space-y-5">
                {["Basic Plan", "Pro Plan", "Enterprise"].map((item, index) => (
                  <div key={item}>
                    <div className="mb-2 flex items-center justify-between text-[11px]">
                      <div className="flex items-center gap-2">
                        <span className={cn("h-4 w-4 rounded-full", isDark ? "bg-white/25" : "bg-black/30")} />
                        <span>{item}</span>
                      </div>
                      <span>{["$48,430", "$32,540", "$17,570"][index]}</span>
                    </div>
                    <div className={cn("h-1 rounded-full", isDark ? "bg-white/10" : "bg-black/10")}>
                      <div className="h-full rounded-full bg-[#6687ec]" style={{ width: `${82 - index * 18}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ChairConfiguratorScene() {
  return (
    <div className="relative h-full w-full overflow-hidden bg-[radial-gradient(circle_at_50%_68%,rgba(255,255,255,0.18),transparent_16rem),linear-gradient(135deg,#11151b,#07090c)] p-5 text-white">
      <div className="absolute left-6 top-6 space-y-3">
        {[0, 1, 2].map((item) => (
          <div key={item} className="h-16 w-16 rounded-md border border-white/10 bg-white/[0.04] p-2">
            <div className="chair-mini" />
          </div>
        ))}
      </div>

      <div className="absolute inset-y-16 left-[23%] right-[26%]">
        <div className="chair-stage">
          <div className="chair-back" />
          <div className="chair-seat" />
          <div className="chair-leg chair-leg-left" />
          <div className="chair-leg chair-leg-right" />
          <div className="chair-leg chair-leg-back-left" />
          <div className="chair-leg chair-leg-back-right" />
        </div>
      </div>

      <div className="absolute right-5 top-5 w-[31%] space-y-2">
        <ConfiguratorPanel title="Материал" items={5} />
        <ConfiguratorPanel title="Цвет" items={5} warm />
        <div className="rounded-md border border-white/10 bg-white/[0.045] p-3">
          <p className="mb-3 text-xs font-semibold">Окружение</p>
          <div className="grid grid-cols-4 gap-2">
            {[0, 1, 2, 3].map((item) => (
              <div
                key={item}
                className="aspect-[4/3] rounded-sm bg-[radial-gradient(circle_at_50%_40%,rgba(255,255,255,0.65),transparent_26%),linear-gradient(135deg,#222936,#555d6b)]"
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function ConfiguratorPanel({
  title,
  items,
  warm = false,
}: {
  title: string;
  items: number;
  warm?: boolean;
}) {
  return (
    <div className="rounded-md border border-white/10 bg-white/[0.045] p-3">
      <p className="mb-3 text-xs font-semibold">{title}</p>
      <div className="flex gap-4">
        {Array.from({ length: items }).map((_, index) => (
          <span
            key={index}
            className={cn(
              "h-6 w-6 rounded-full",
              warm
                ? ["bg-[#f8fafc]", "bg-[#d8c7b0]", "bg-[#bba990]", "bg-[#988b79]", "bg-[#d9dde0]"][index]
                : ["bg-[#c7ccd1]", "bg-[#eef1f2]", "bg-[#f7f8f8]", "bg-[#a4a6a6]", "bg-[#565a5b]"][index],
            )}
          />
        ))}
      </div>
    </div>
  );
}

function FinanceMotionScene() {
  return (
    <div className="relative h-full w-full overflow-hidden bg-[radial-gradient(circle_at_68%_38%,rgba(116,44,255,0.42),transparent_18rem),linear-gradient(135deg,#090913,#13101f)] p-8 text-white">
      <div className="absolute left-8 top-10 max-w-[240px]">
        <h3 className="text-3xl font-semibold leading-tight tracking-normal">Balance management made simple</h3>
        <p className="mt-4 text-sm leading-6 text-white/60">Control your finances, track expenses and achieve your goals.</p>
        <button className="mt-6 rounded-md bg-[#7553ff] px-6 py-3 text-sm font-semibold" type="button">
          Get started
        </button>
      </div>

      <div className="absolute left-[36%] top-7 h-[74%] w-[34%] rotate-[7deg] rounded-lg border border-[#7a4dff] bg-[linear-gradient(135deg,rgba(255,255,255,0.13),rgba(111,45,255,0.12))] p-7 shadow-[0_20px_70px_rgba(90,35,255,0.26)]">
        <p className="text-sm text-white/60">Balance</p>
        <p className="mt-3 text-3xl font-medium tracking-normal">$4,560.00</p>
        <div className="relative mt-10 h-28">
          <svg className="absolute inset-0 h-full w-full" viewBox="0 0 320 130" preserveAspectRatio="none">
            <defs>
              <linearGradient id="purpleChart" x1="0" x2="1" y1="0" y2="0">
                <stop stopColor="#7e4dff" />
                <stop offset="1" stopColor="#d6b8ff" />
              </linearGradient>
            </defs>
            <polyline
              points="0,104 22,92 44,112 66,70 88,96 110,56 132,105 154,74 176,89 198,44 220,100 242,42 264,82 286,36 320,62"
              fill="none"
              stroke="url(#purpleChart)"
              strokeWidth="6"
            />
          </svg>
          <div className="absolute bottom-0 flex w-full justify-between text-xs text-white/45">
            {["Jan", "Feb", "Mar", "Apr", "May", "Jun"].map((month) => (
              <span key={month}>{month}</span>
            ))}
          </div>
        </div>
      </div>

      <div className="absolute right-8 top-[24%] h-[52%] w-[21%] rounded-lg border border-[#5d40c7] bg-white/[0.04] p-5">
        <p className="text-sm text-white/60">Spending</p>
        <div className="mt-3 flex items-end justify-between">
          <p className="text-2xl font-medium tracking-normal">$2,560</p>
          <p className="text-xs text-[#b58cff]">+12%</p>
        </div>
        <div className="mx-auto mt-9 h-28 w-28 rounded-full bg-[conic-gradient(#874cff_0_64%,rgba(255,255,255,0.09)_64%_100%)] p-5">
          <div className="h-full w-full rounded-full bg-[#14101f]" />
        </div>
      </div>
    </div>
  );
}
