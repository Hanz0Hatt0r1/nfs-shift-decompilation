
undefined4 * __fastcall FUN_00835050(int param_1,int *param_2)

{
  void *this;
  undefined4 *puVar1;

  this = (void *)FUN_008868c0(0x54);
  if (this != (void *)0x0) {
    puVar1 = FUN_00853790(this,param_2);
    FUN_00834a60(param_1,6,(int)puVar1);
    return puVar1;
  }
  FUN_00834a60(param_1,6,0);
  return (undefined4 *)0x0;
}
