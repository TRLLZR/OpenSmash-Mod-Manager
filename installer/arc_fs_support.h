/* Read-only Skyline RomFS overlay and SDK operation used by ARCropolis.
 * Included in a PRIVATE copy of
 * upstream nnfs.c, so all path and mount checks remain those of OpenSmash.
 * FileTimeStamp ABI: ultimate-research/nnsdk-rs src/nn/fs.rs;
 * POSIX seconds / validity: switchbrew/libnx services/fs.h. */
/* Skyline injects this directory into the console's RomFS. Loading a translated
 * NRO alone does not make nn::fs existence/read/directory operations see it.
 * Return -1 for unrelated paths, otherwise the real host entry's existence.
 * The caller retains MK_ROM write denial and ordinary mount-table checks. */
static int arc_plugin_view(Mount *mount, const char *rel, char *out) {
    const char *enabled = getenv("SSBU_SKYLINE"), *sd = getenv("SSBU_SD");
    const char prefix[] = "skyline\\plugins";
    const size_t n = sizeof(prefix) - 1;
    if (mount->kind != MK_ROM || !enabled || strcmp(enabled, "1") || !sd || !sd[0]
        || _strnicmp(rel, prefix, n) || (rel[n] && rel[n] != '\\')) return -1;
    /* split_path has normalized separators. Do not let an overlay reference
     * escape its selected plugin folder through Win32 path normalization. */
    const char *part = rel;
    for (const char *p = rel;; p++) {
        if (*p == ':' || *p == '/' || (*p && (unsigned char)*p < 32)) return 0;
        if (*p == '\\' || !*p) {
            size_t length = (size_t)(p - part);
            if (!length || part[length - 1] == '.' || part[length - 1] == ' ') return 0;
            if (!*p) break;
            part = p + 1;
        }
    }
    int length = snprintf(out, MAX_PATH, "%s\\atmosphere\\contents\\01006A800016E000\\romfs\\%s", sd, rel);
    if (length < 0 || length >= MAX_PATH) return 0;
    return GetFileAttributesA(out) != INVALID_FILE_ATTRIBUTES;
}

static uint64_t arc_posix_time(FILETIME ft) {
    ULARGE_INTEGER value;
    value.LowPart = ft.dwLowDateTime;
    value.HighPart = ft.dwHighDateTime;
    return value.QuadPart >= 116444736000000000ULL
        ? (value.QuadPart - 116444736000000000ULL) / 10000000ULL : 0;
}
static void arc_GetFileTimeStamp(Ctx *c) {
    uint64_t out = c->x[0];
    const char *guest = (const char *)(uintptr_t)c->x[1];
    Mount *mount;
    char rel[MAX_PATH], host[MAX_PATH];
    WIN32_FILE_ATTRIBUTE_DATA data;
    fs_lock();
    uint32_t result = split_path(guest, &mount, rel);
    if (!result && (!view_path(mount, rel, host) ||
        !GetFileAttributesExA(host, GetFileExInfoStandard, &data)))
        result = RESULT_PATH_NOT_FOUND;
    fs_unlock();
    if (!result && out) {
        memset((void *)(uintptr_t)out, 0, 32);
        wr64(out, arc_posix_time(data.ftCreationTime));
        wr64(out + 8, arc_posix_time(data.ftLastWriteTime));
        wr64(out + 16, arc_posix_time(data.ftLastAccessTime));
        wr8(out + 24, 1);
    }
    c->x[0] = result;
}
