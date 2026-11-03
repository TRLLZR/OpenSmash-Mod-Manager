/* Additional SDK operation used by ARCropolis. Included in a PRIVATE copy of
 * upstream nnfs.c, so all path and mount checks remain those of OpenSmash.
 * FileTimeStamp ABI: ultimate-research/nnsdk-rs src/nn/fs.rs;
 * POSIX seconds / validity: switchbrew/libnx services/fs.h. */
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
