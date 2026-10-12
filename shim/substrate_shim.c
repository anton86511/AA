/*
 * Minimal CydiaSubstrate replacement for sideloaded apps.
 * iSponsorBlock only imports MSHookMessageEx, which can be implemented
 * with the Objective-C runtime alone (no code patching needed).
 */
#include <stddef.h>

typedef struct objc_class *Class;
typedef struct objc_selector *SEL;
typedef struct objc_method *Method;
typedef void (*IMP)(void);
typedef signed char BOOL_T;

extern Method class_getInstanceMethod(Class cls, SEL name);
extern IMP method_getImplementation(Method m);
extern const char *method_getTypeEncoding(Method m);
extern BOOL_T class_addMethod(Class cls, SEL name, IMP imp, const char *types);
extern IMP method_setImplementation(Method m, IMP imp);

__attribute__((visibility("default")))
void MSHookMessageEx(Class cls, SEL sel, IMP imp, IMP *result) {
    Method m = cls ? class_getInstanceMethod(cls, sel) : NULL;
    if (!m) {
        if (result) *result = NULL;
        return;
    }
    IMP old = method_getImplementation(m);
    if (result) *result = old;
    /* If the method is inherited, add an override on this class instead of
       modifying the superclass; otherwise replace it in place. */
    if (!class_addMethod(cls, sel, imp, method_getTypeEncoding(m)))
        method_setImplementation(m, imp);
}
