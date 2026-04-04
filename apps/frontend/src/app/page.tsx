import { HomePageSurface } from "@/app/HomePageSurface";
import { getBlogPostsCached, getProjectsCached, getSiteSettings } from "@/shared/api/client";
import { fallbackPosts, fallbackProjects, fallbackSettings } from "@/shared/mock/content";

export default async function HomePage() {
  try {
    const [settings, projects, posts] = await Promise.all([
      getSiteSettings({ next: { revalidate: 60 } }),
      getProjectsCached({ featuredOnly: true }, { next: { revalidate: 60 } }),
      getBlogPostsCached(undefined, { next: { revalidate: 60 } })
    ]);

    return (
      <HomePageSurface
        initialSettings={settings}
        initialProjects={projects}
        initialPosts={posts.slice(0, 2)}
      />
    );
  } catch {
    return (
      <HomePageSurface
        initialSettings={fallbackSettings}
        initialProjects={fallbackProjects}
        initialPosts={fallbackPosts}
      />
    );
  }
  /*
  const { locale } = useI18n();
  const [settings, setSettings] = useState<SiteSettings>(fallbackSettings);
  const [projects, setProjects] = useState<Project[]>(fallbackProjects);
  const [posts, setPosts] = useState<BlogPost[]>(fallbackPosts);
  const [contactOpened, setContactOpened] = useState(false);

  useEffect(() => {
    Promise.all([getSiteSettings(), getProjects({ featuredOnly: true }), getBlogPosts()]).then(
      ([siteSettings, nextProjects, nextPosts]) => {
        setSettings(siteSettings);
        setProjects(nextProjects);
        setPosts(nextPosts.slice(0, 2));
      }
    );
  }, []);

  return (
    <>
      <div className="page-shell space-y-8 py-6 md:space-y-10 md:py-8">
        <Header email={settings.contact_email} onOpenContact={() => setContactOpened(true)} />

        <section className="space-y-6">
          <div className="space-y-3">
            <h1 className="text-4xl font-semibold tracking-tight text-slate-900 md:text-5xl">
              {locale === "ru" ? "Любимые проекты" : "Favorite projects"}
            </h1>
            <p className="font-display-italic max-w-3xl text-base leading-7 text-slate-600 md:text-lg">
              {locale === "ru"
                ? "ИИ-помощник: локальная нейронка, для помощи в выборе одежды"
                : "AI assistant: a local neural network for helping with outfit selection"}
            </p>
          </div>
          <ChatWindow settings={settings} />
        </section>

        {projects.map((project) => (
          <ProjectCardWindow key={project.id} project={project} locale={locale} />
        ))}

        <section className="space-y-6">
          <div className="space-y-6">
            {posts.map((post) => (
              <BlogCard key={post.id} post={post} locale={locale} />
            ))}
          </div>
          <Link
            href="/blog"
            className="inline-flex rounded-full border border-slate-300 px-5 py-3 text-sm font-medium text-slate-900 transition hover:border-slate-400"
          >
            {locale === "ru" ? "Все записи блога" : "All blog posts"}
          </Link>
        </section>

        <section>
          <AboutSection settings={settings} locale={locale} />
        </section>
      </div>
      <div className="page-shell">
        <Footer settings={settings} />
      </div>
      <ContactModal opened={contactOpened} onClose={() => setContactOpened(false)} />
    </>
  );
  */
}
