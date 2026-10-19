
int * __fastcall FUN_00838410(int param_1,undefined4 param_2,undefined4 param_3)

{
  int iVar1;
  int *local_8;

  local_8 = (int *)0x0;
  if (*(char *)(param_1 + 0x18) == '\0') {
    if (*(int *)(param_1 + 8) == 0) {
      iVar1 = (**(code **)(**(int **)(param_1 + 0x38) + 0x48))
                        (*(int **)(param_1 + 0x38),param_2,&local_8);
      if (iVar1 < 0) {
        return (int *)0x0;
      }
    }
    else if (*(int *)(param_1 + 8) == 1) {
      iVar1 = (**(code **)(**(int **)(param_1 + 0x38) + 0x48))
                        (*(int **)(param_1 + 0x38),param_3,param_2,&local_8);
      if (iVar1 < 0) {
        return (int *)0x0;
      }
    }
  }
  else {
    local_8 = *(int **)(param_1 + 0x38);
    (**(code **)(*local_8 + 4))(local_8);
  }
  return local_8;
}
