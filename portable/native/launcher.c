/* Reapdf Windows GUI bootstrap. No shell, installation, or elevation. */
#define UNICODE
#define _UNICODE
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wchar.h>
#include <stdio.h>

static BOOL cancelled=FALSE;
static LRESULT CALLBACK splash_proc(HWND window,UINT msg,WPARAM w,LPARAM l){
    if(msg==WM_CLOSE){cancelled=TRUE;return 0;}
    if(msg==WM_PAINT){
        PAINTSTRUCT ps;HDC dc=BeginPaint(window,&ps);RECT r;GetClientRect(window,&r);
        HBRUSH white=CreateSolidBrush(RGB(250,252,251));FillRect(dc,&r,white);DeleteObject(white);
        RECT logo={36,35,104,103};HBRUSH green=CreateSolidBrush(RGB(28,104,83));FillRect(dc,&logo,green);DeleteObject(green);
        SetBkMode(dc,TRANSPARENT);HFONT font=CreateFontW(-46,0,0,0,FW_BOLD,0,0,0,DEFAULT_CHARSET,0,0,CLEARTYPE_QUALITY,0,L"Segoe UI");HGDIOBJ old=SelectObject(dc,font);
        SetTextColor(dc,RGB(255,255,255));DrawTextW(dc,L"R",-1,&logo,DT_CENTER|DT_VCENTER|DT_SINGLELINE);SelectObject(dc,old);DeleteObject(font);
        font=CreateFontW(-30,0,0,0,FW_SEMIBOLD,0,0,0,DEFAULT_CHARSET,0,0,CLEARTYPE_QUALITY,0,L"Segoe UI");old=SelectObject(dc,font);
        SetTextColor(dc,RGB(32,48,57));TextOutW(dc,125,38,L"Reapdf",6);SelectObject(dc,old);DeleteObject(font);
        RECT status={125,81,460,130};SetTextColor(dc,RGB(80,100,93));DrawTextW(dc,L"Preparando tu espacio de trabajo...",-1,&status,DT_LEFT|DT_WORDBREAK);
        EndPaint(window,&ps);return 0;
    }
    return DefWindowProcW(window,msg,w,l);
}
static int fail(const wchar_t *message,const wchar_t *log){
    wchar_t detail[2048];swprintf(detail,2048,L"%ls\n\n%ls%ls",message,log&&*log?L"Detalle del inicio: ":L"",log?log:L"");
    MessageBoxW(NULL,detail,L"Reapdf — no se pudo iniciar",MB_OK|MB_ICONERROR);return 1;
}
int WINAPI wWinMain(HINSTANCE instance,HINSTANCE previous,PWSTR arguments,int show){
    (void)previous;(void)arguments;(void)show;
    wchar_t root[32768],python[32768],script[32768],command[32768],temp[MAX_PATH],ready[MAX_PATH],log[MAX_PATH]=L"";
    DWORD length=GetModuleFileNameW(NULL,root,32768);
    if(!length||length>=32768)return fail(L"No se pudo localizar Reapdf.exe.",NULL);
    wchar_t *slash=wcsrchr(root,L'\\');if(!slash)return fail(L"Ruta de inicio no compatible.",NULL);*slash=0;
    if(wcslen(root)>14000)return fail(L"Extrae el programa en una ruta mas corta.",NULL);
    swprintf(python,32768,L"%ls\\runtime\\python.exe",root);swprintf(script,32768,L"%ls\\app\\launcher.py",root);
    if(GetFileAttributesW(python)==INVALID_FILE_ATTRIBUTES||GetFileAttributesW(script)==INVALID_FILE_ATTRIBUTES)return fail(L"Extrae TODO el ZIP antes de abrir Reapdf.exe. Mantiene juntos runtime, app y Reapdf.exe.",NULL);
    DWORD temp_length=GetTempPathW(MAX_PATH,temp);
    if(!temp_length||temp_length>=MAX_PATH-14||!GetTempFileNameW(temp,L"rpf",0,ready))return fail(L"No se pudo crear un archivo temporal de inicio.",NULL);
    /* User-local diagnostics, never next to potentially read-only program files. */
    DWORD n=GetEnvironmentVariableW(L"LOCALAPPDATA",log,MAX_PATH);
    if(!n||n>MAX_PATH-90){DeleteFileW(ready);return fail(L"No se encontro una carpeta local escribible para el registro de inicio.",NULL);}
    wcscat(log,L"\\Reapdf");CreateDirectoryW(log,NULL);wcscat(log,L"\\logs");CreateDirectoryW(log,NULL);
    size_t base=wcslen(log);swprintf(log+base,MAX_PATH-base,L"\\inicio-%lu.log",GetCurrentProcessId());
    SECURITY_ATTRIBUTES security={sizeof(SECURITY_ATTRIBUTES),NULL,TRUE};
    HANDLE output=CreateFileW(log,GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE,&security,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    HANDLE input=CreateFileW(L"NUL",GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE,&security,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,NULL);
    if(output==INVALID_HANDLE_VALUE||input==INVALID_HANDLE_VALUE){if(output!=INVALID_HANDLE_VALUE)CloseHandle(output);if(input!=INVALID_HANDLE_VALUE)CloseHandle(input);DeleteFileW(ready);return fail(L"No se pudo preparar el registro de inicio.",log);}
    HANDLE job=CreateJobObjectW(NULL,NULL);JOBOBJECT_EXTENDED_LIMIT_INFORMATION limit={0};limit.BasicLimitInformation.LimitFlags=JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
    if(!job||!SetInformationJobObject(job,JobObjectExtendedLimitInformation,&limit,sizeof(limit))){if(job)CloseHandle(job);CloseHandle(output);CloseHandle(input);DeleteFileW(ready);return fail(L"No se pudo preparar el cierre del programa.",log);}
    STARTUPINFOW startup={0};startup.cb=sizeof(startup);startup.dwFlags=STARTF_USESTDHANDLES|STARTF_USESHOWWINDOW;startup.wShowWindow=SW_HIDE;startup.hStdOutput=output;startup.hStdError=output;startup.hStdInput=input;
    PROCESS_INFORMATION process={0};
    swprintf(command,32768,L"\"%ls\" -I \"%ls\" --desktop --require-desktop --ready-file \"%ls\"",python,script,ready);
    BOOL started=CreateProcessW(python,command,NULL,NULL,TRUE,CREATE_NO_WINDOW|CREATE_SUSPENDED,NULL,root,&startup,&process);
    CloseHandle(output);CloseHandle(input);
    if(!started){CloseHandle(job);DeleteFileW(ready);return fail(L"Windows no pudo iniciar el motor incluido. Comprueba que el equipo sea Windows 10/11 de 64 bits y que el paquete este completo.",log);}
    if(!AssignProcessToJobObject(job,process.hProcess)){TerminateProcess(process.hProcess,1);CloseHandle(process.hThread);CloseHandle(process.hProcess);CloseHandle(job);DeleteFileW(ready);return fail(L"Las restricciones del equipo impiden iniciar el proceso de Reapdf.",log);}
    ResumeThread(process.hThread);CloseHandle(process.hThread);
    WNDCLASSW wc={0};wc.lpfnWndProc=splash_proc;wc.hInstance=instance;wc.lpszClassName=L"ReapdfStartup";wc.hCursor=LoadCursorW(NULL,IDC_ARROW);wc.hIcon=LoadIconW(instance,MAKEINTRESOURCEW(1));RegisterClassW(&wc);
    HWND splash=CreateWindowExW(WS_EX_APPWINDOW,wc.lpszClassName,L"Reapdf",WS_CAPTION|WS_SYSMENU,(GetSystemMetrics(SM_CXSCREEN)-500)/2,(GetSystemMetrics(SM_CYSCREEN)-180)/2,500,180,NULL,NULL,instance,NULL);
    if(splash){ShowWindow(splash,SW_SHOW);UpdateWindow(splash);}
    ULONGLONG deadline=GetTickCount64()+60000;BOOL prepared=FALSE;
    while(WaitForSingleObject(process.hProcess,0)==WAIT_TIMEOUT&&!cancelled&&GetTickCount64()<deadline){
        MSG message;while(PeekMessageW(&message,NULL,0,0,PM_REMOVE)){TranslateMessage(&message);DispatchMessageW(&message);}
        WIN32_FILE_ATTRIBUTE_DATA status;
        if(GetFileAttributesExW(ready,GetFileExInfoStandard,&status)&&(status.nFileSizeLow||status.nFileSizeHigh)){prepared=TRUE;break;}
        Sleep(80);
    }
    if(splash)DestroyWindow(splash);DeleteFileW(ready);
    if(cancelled||!prepared){TerminateJobObject(job,1);WaitForSingleObject(process.hProcess,5000);CloseHandle(process.hProcess);CloseHandle(job);return cancelled?0:fail(L"No se pudo abrir la ventana. Reapdf necesita Edge o Chrome instalado y permiso para ejecutar aplicaciones locales. Consulta el registro para ver la causa.",log);}
    WaitForSingleObject(process.hProcess,INFINITE);DWORD code=1;GetExitCodeProcess(process.hProcess,&code);CloseHandle(process.hProcess);CloseHandle(job);
    return code?fail(L"Reapdf termino con un error. Tus proyectos guardados permanecen en sus carpetas.",log):0;
}
